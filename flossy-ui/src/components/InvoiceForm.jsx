import { useState, useEffect } from 'react';
import { useSession } from '@clerk/clerk-react';
import { COUNTRY_CODES } from '../utils/countryCodes';
import { CURRENCIES } from '../utils/currencies';
import '../styles/invoice_form.css';

const getFlagEmoji = (isoCode) => {
    if (!isoCode) return "🌐";
    return isoCode
        .toUpperCase()
        .replace(/./g, (char) =>
            String.fromCodePoint(char.charCodeAt(0) + 127397)
        );
};

const API = import.meta.env.VITE_API_BASE_URL;

const EXCHANGE_RATES = {
    INR: 1,
    USD: 0.012,
    AFN: 0.80
};

const convertPrice = (amount, fromCurrency, toCurrency) => {
    if (!amount) return 0;
    const fromRate = EXCHANGE_RATES[fromCurrency] || 1;
    const toRate = EXCHANGE_RATES[toCurrency] || 1;
    // Base is INR. INR value = amount / fromRate. New Value = INR value * toRate.
    // Wait, rates ARE relative to INR (e.g. 1 INR = 0.012 USD).
    // So: Amount(INR) * Rate(USD) = Amount(USD).
    // General: (Amount / Rate(From)) * Rate(To)
    const val = (parseFloat(amount) / fromRate) * toRate;
    return parseFloat(val.toFixed(2));
};

const InvoiceForm = ({ patientsList, onInvoiceCreated, downloadInvoice, editingInvoice, onCancelEdit, preSelectedPatient, onPatientChange }) => {
    const { session } = useSession();
    const [patientName, setPatientName] = useState("");
    const [currency, setCurrency] = useState("INR");
    const [discount, setDiscount] = useState(0);
    const [items, setItems] = useState([{ treatment_name: "", cost: 0, discount: 0, discount_type: "flat", treatment_date: new Date().toISOString().split('T')[0] }]);
    const [payments, setPayments] = useState([{ payment_method: "UPI", amount: 0, paid_on: new Date().toISOString().split('T')[0] }]);
    const [invoiceDate, setInvoiceDate] = useState(new Date().toISOString().split('T')[0]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isManualPayment, setIsManualPayment] = useState(false); // Track if user manually edited payment
    const [patientSearch, setPatientSearch] = useState("");
    const [showPatientSuggestions, setShowPatientSuggestions] = useState(false);
    const [treatmentSearchTerm, setTreatmentSearchTerm] = useState("");
    const [activeTreatmentIdx, setActiveTreatmentIdx] = useState(null);
    const [catalog, setCatalog] = useState([]);
    const [patientPhone, setPatientPhone] = useState("");
    const [countryCode, setCountryCode] = useState("+91");
    const [showCountrySearch, setShowCountrySearch] = useState(false);
    const [showCurrencySearch, setShowCurrencySearch] = useState(false);
    const [currencySearch, setCurrencySearch] = useState("");

    // Populate form if editing
    useEffect(() => {
        if (editingInvoice) {
            setPatientName(editingInvoice.patient_name || "");
            setPatientSearch(editingInvoice.patient_name || ""); // Pre-fill search
            setCurrency(editingInvoice.currency || "INR");
            setDiscount(editingInvoice.discount || 0);

            // Format dates from API (ISO) to YYYY-MM-DD
            const invDate = editingInvoice.date ? new Date(editingInvoice.date).toISOString().split('T')[0] : new Date().toISOString().split('T')[0];
            setInvoiceDate(invDate);

            if (editingInvoice.items && editingInvoice.items.length > 0) {
                setItems(editingInvoice.items.map(i => ({
                    ...i,
                    treatment_date: i.treatment_date ? new Date(i.treatment_date).toISOString().split('T')[0] : new Date().toISOString().split('T')[0],
                    discount_type: i.discount_type || "flat" // API usually returns calculated discount, we assume flat for simplicity in edit reverse eng? Or just flat. 
                })));
            }

            if (editingInvoice.payments && editingInvoice.payments.length > 0) {
                setPayments(editingInvoice.payments.map(p => ({
                    ...p,
                    paid_on: p.paid_on ? new Date(p.paid_on).toISOString().split('T')[0] : new Date().toISOString().split('T')[0]
                })));
                setIsManualPayment(true); // Don't auto-overwrite amounts
            }
        }
    }, [editingInvoice]);

    // Handle pre-selected patient from dashboard
    useEffect(() => {
        if (!editingInvoice && preSelectedPatient) {
            setPatientName(preSelectedPatient);
            setPatientSearch(preSelectedPatient);
        }
    }, [preSelectedPatient, editingInvoice]);

    // Fetch Treatment Catalog
    useEffect(() => {
        async function fetchCatalog() {
            try {
                const res = await fetch(`${API}/api/treatments`);
                if (res.ok) {
                    const data = await res.json();
                    setCatalog(data.treatments);
                }
            } catch (err) {
                console.error("Failed to fetch catalog", err);
            }
        }
        fetchCatalog();
    }, []);

    // Notify parent when patient changes
    useEffect(() => {
        if (onPatientChange) {
            onPatientChange(patientName);
        }
    }, [patientName, onPatientChange]);

    const currencySymbol = CURRENCIES.find(c => c.code === currency)?.symbol || (currency === 'INR' ? '₹' : '$');

    const calculateItemDiscountAmount = (item) => {
        const cost = parseFloat(item.cost) || 0;
        const disc = parseFloat(item.discount) || 0;
        if (item.discount_type === "percent") {
            return (cost * disc) / 100;
        }
        return disc;
    };

    const subtotal = items.reduce((sum, item) => sum + (parseFloat(item.cost) || 0), 0);
    const totalItemDiscount = items.reduce((sum, item) => sum + calculateItemDiscountAmount(item), 0);

    const totalAmount = Math.max(0, subtotal - totalItemDiscount);
    const totalPaid = payments.reduce((sum, pay) => sum + (parseFloat(pay.amount) || 0), 0);
    const amountDue = totalAmount - totalPaid;

    // Auto-fill payment amount if not manual
    useEffect(() => {
        if (!isManualPayment && payments.length === 1 && !editingInvoice) { // Only auto-fill for new invoices to avoid overwriting existing data
            const newPayments = [...payments];
            newPayments[0].amount = Math.max(0, totalAmount);
            setPayments(newPayments);
        }
    }, [totalAmount, isManualPayment, editingInvoice]);

    // Handle Currency Change & Auto-Convert Items
    const handleCurrencyChange = (newCurrency) => {
        const prevCurrency = currency;
        setCurrency(newCurrency);

        // Convert Invoice Items
        const convertedItems = items.map(item => ({
            ...item,
            cost: convertPrice(item.cost, prevCurrency, newCurrency),
            discount: item.discount_type === 'flat' ? convertPrice(item.discount, prevCurrency, newCurrency) : item.discount
        }));
        setItems(convertedItems);

        // Convert Payments
        const convertedPayments = payments.map(p => ({
            ...p,
            amount: convertPrice(p.amount, prevCurrency, newCurrency)
        }));
        setPayments(convertedPayments);
    };

    const addItem = () => {
        setItems([...items, { treatment_name: "", cost: 0, discount: 0, discount_type: "flat", treatment_date: new Date().toISOString().split('T')[0] }]);
    };

    const removeItem = (index) => {
        if (items.length > 1) {
            setItems(items.filter((_, i) => i !== index));
        }
    };

    const updateItem = (index, field, value) => {
        const newItems = [...items];
        newItems[index] = { ...newItems[index], [field]: value }; // Correctly copy the object

        // Auto-fill cost if treatment name matches catalog
        if (field === "treatment_name") {
            const match = catalog.find(t => t.name.toLowerCase() === value.toLowerCase());
            if (match) {
                // Convert default INR cost to current currency
                newItems[index].cost = convertPrice(match.cost, 'INR', currency);
            }
        }

        setItems(newItems);
    };

    const addPayment = () => {
        setPayments([...payments, { payment_method: "UPI", amount: 0, paid_on: new Date().toISOString().split('T')[0] }]);
        setIsManualPayment(true); // Once they add another payment, it's manual
    };

    const removePayment = (index) => {
        if (payments.length > 1) {
            setPayments(payments.filter((_, i) => i !== index));
        }
    };

    const updatePayment = (index, field, value) => {
        const newPayments = [...payments];
        newPayments[index] = { ...newPayments[index], [field]: value };
        // If user manually edits amount, stop auto-updating it
        if (field === "amount") {
            setIsManualPayment(true);
        }
        setPayments(newPayments);
    };
    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!patientName) return alert("Please select a patient.");
        if (items.some(it => !it.treatment_name || (it.treatment_name === "Other" && !it.custom_name) || it.cost < 0)) {
            return alert("Please fill all treatment details with valid costs.");
        }

        setIsSubmitting(true);
        try {
            const token = await session.getToken({ template: "default" });

            const url = editingInvoice ? `${API}/api/invoices/${editingInvoice.id}` : `${API}/api/invoices`;
            const method = editingInvoice ? "PUT" : "POST";

            const res = await fetch(url, {
                method: method,
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({
                    patient_name: patientName,
                    discount: 0,
                    items: items.map(it => {
                        return {
                            ...it,
                            treatment_name: it.treatment_name === "Other" ? it.custom_name : it.treatment_name,
                            cost: parseFloat(it.cost),
                            discount: calculateItemDiscountAmount(it)
                        };
                    }),
                    payments: payments.map(p => ({ ...p, amount: parseFloat(p.amount) })),
                    currency: currency,
                    date: invoiceDate
                })
            });

            if (res.ok) {
                const result = await res.json();
                alert(`Invoice ${editingInvoice ? "updated" : "generated"} successfully!`);

                // If editing, don't auto-download on save unless requested? Just alert for now.
                if (!editingInvoice && downloadInvoice && result.invoice_id) {
                    downloadInvoice(result.invoice_id, result.invoice_number, true);
                }

                // Reset form or trigger callback
                if (onInvoiceCreated) onInvoiceCreated();

                // Clear State
                setPatientName("");
                setPatientSearch("");
                setDiscount(0);
                setItems([{ treatment_name: "", cost: 0, discount: 0, discount_type: "flat", treatment_date: new Date().toISOString().split('T')[0] }]);
                setPayments([{ payment_method: "UPI", amount: 0, paid_on: new Date().toISOString().split('T')[0] }]);
                setIsManualPayment(false);

                if (editingInvoice && onCancelEdit) onCancelEdit(); // Exit edit mode

            } else {
                const err = await res.json();
                alert("Failed to save invoice: " + (err.detail || "Unknown error"));
            }
        } catch (err) {
            console.error(err);
            alert("Error saving invoice.");
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="invoice-form-container">
            <form onSubmit={handleSubmit} className="premium-form">
                {editingInvoice && (
                    <div style={{ background: "#f39c1222", border: "1px solid #f39c12", padding: "10px", borderRadius: "8px", marginBottom: "15px", color: "#f39c12", fontWeight: "bold", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span>Editing Invoice #{editingInvoice.invoice_number}</span>
                        <button type="button" onClick={onCancelEdit} style={{ background: "transparent", border: "1px solid #f39c12", color: "#f39c12", padding: "4px 8px", borderRadius: "4px", cursor: "pointer" }}>Cancel</button>
                    </div>
                )}                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '20px', marginBottom: '1rem' }}>
                    <div className="form-group" style={{ position: "relative" }}>
                        <label>Select Patient</label>
                        <div className="patient-search-container" style={{ position: "relative" }}>
                            <div className="input-icon-wrapper" style={{ height: "45px" }}>
                                <i className="fas fa-search"></i>
                                <input
                                    type="text"
                                    placeholder="Search patient name..."
                                    value={patientSearch || patientName}
                                    onChange={(e) => {
                                        setPatientSearch(e.target.value);
                                        setShowPatientSuggestions(true);
                                        if (patientName) setPatientName("");
                                    }}
                                    onFocus={() => setShowPatientSuggestions(true)}
                                    className="dashboard-input"
                                    style={{ height: "100%" }}
                                />
                            </div>

                            {showPatientSuggestions && (patientSearch.trim() !== "" || (patientsList && patientsList.length > 0)) && (
                                <div className="patient-suggestions elegant-scroll" style={{
                                    position: "absolute", top: "100%", left: 0, right: 0,
                                    zIndex: 101, background: "#1a1a1a", border: "1px solid #444",
                                    borderRadius: "8px", marginTop: "5px", maxHeight: "180px",
                                    overflowY: "auto", boxShadow: "0 10px 25px rgba(0,0,0,0.5)"
                                }}>
                                    {patientsList
                                        .filter(p => {
                                            if (!p) return false;
                                            const search = (patientSearch || "").toLowerCase().trim();
                                            if (!search) return true;
                                            const name = (p.name || "").toLowerCase();
                                            const phone = (p.phone || "").toLowerCase();
                                            const email = (p.email || "").toLowerCase();
                                            return name.includes(search) || phone.includes(search) || email.includes(search);
                                        })
                                        .map((p, i) => (
                                            <div
                                                key={p.id}
                                                onClick={() => {
                                                    setPatientName(p.name);
                                                    setPatientSearch(p.name);
                                                    // Extract country code if present
                                                    const phoneStr = p.phone || "";
                                                    const match = COUNTRY_CODES.find(c => phoneStr.startsWith(c.code));
                                                    if (match) {
                                                        setCountryCode(match.code);
                                                        setPatientPhone(phoneStr.replace(match.code, ""));
                                                    } else {
                                                        setPatientPhone(phoneStr);
                                                    }
                                                    setShowPatientSuggestions(false);
                                                }}
                                                style={{
                                                    padding: "10px 15px", cursor: "pointer", borderBottom: "1px solid #333",
                                                    background: patientName === p.name ? "#2a2a2a" : "transparent"
                                                }}
                                                onMouseEnter={(e) => e.currentTarget.style.background = "#2a2a2a"}
                                                onMouseLeave={(e) => e.currentTarget.style.background = patientName === p.name ? "#2a2a2a" : "transparent"}
                                            >
                                                <div style={{ fontWeight: "600", color: "#fff" }}>{p.name}</div>
                                                {p.phone && p.phone !== "null" && !p.phone.startsWith("TEMP_") && <div style={{ fontSize: "0.75rem", color: "#888" }}>{p.phone}</div>}
                                            </div>
                                        ))}
                                    {patientsList.filter(p => {
                                        if (!p) return false;
                                        const search = (patientSearch || "").toLowerCase().trim();
                                        if (!search) return true;
                                        const name = (p.name || "").toLowerCase();
                                        const phone = (p.phone || "").toLowerCase();
                                        const email = (p.email || "").toLowerCase();
                                        return name.includes(search) || phone.includes(search) || email.includes(search);
                                    }).length === 0 && (
                                            <div style={{ padding: "15px", color: "#888", textAlign: "center" }}>No patients found.</div>
                                        )}
                                </div>
                            )}
                        </div>
                        {showPatientSuggestions && (
                            <div
                                style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, zIndex: 100 }}
                                onClick={() => setShowPatientSuggestions(false)}
                            ></div>
                        )}
                    </div>

                    <div className="form-group relative" style={{ flex: 1 }}>
                        <label>DATE</label>
                        <div className="input-icon-wrapper" style={{ height: "45px" }}>
                            <i
                                className="fas fa-calendar-alt"
                                onClick={(e) => {
                                    const input = e.currentTarget.parentElement.querySelector('input');
                                    if (input) input.showPicker();
                                }}
                                style={{ cursor: 'pointer', pointerEvents: 'auto' }}
                            ></i>
                            <input
                                type="date"
                                value={invoiceDate}
                                onChange={(e) => setInvoiceDate(e.target.value)}
                                className="dashboard-input"
                                style={{ colorScheme: "dark", height: "100%" }}
                                onClick={(e) => e.target.showPicker()}
                            />
                        </div>
                    </div>

                    <div className="form-group relative" style={{ flex: 1 }}>
                        <label>CURRENCY</label>
                        <div className="input-icon-wrapper" style={{ height: "45px" }}>
                            <i className="fas fa-coins"></i>
                            <input
                                type="text"
                                value={showCurrencySearch ? currencySearch : `${currency} (${currencySymbol})`}
                                onFocus={() => { setShowCurrencySearch(true); setCurrencySearch(""); }}
                                onChange={(e) => setCurrencySearch(e.target.value)}
                                placeholder="Search..."
                                className="dashboard-input"
                                style={{
                                    background: "#222", border: "1px solid #333", borderRadius: "8px",
                                    color: "#fff", width: "100%", outline: "none", height: "100%"
                                }}
                            />
                            {showCurrencySearch && (
                                <div className="elegant-scroll" style={{
                                    position: "absolute", top: "100%", left: 0, right: 0,
                                    zIndex: 105, background: "#1a1a1a", border: "1px solid #444",
                                    borderRadius: "8px", marginTop: "5px", maxHeight: "200px",
                                    overflowY: "auto", boxShadow: "0 10px 25px rgba(0,0,0,0.5)"
                                }}>
                                    {CURRENCIES.filter(c =>
                                        c.name.toLowerCase().includes(currencySearch.toLowerCase()) ||
                                        c.code.toLowerCase().includes(currencySearch.toLowerCase())
                                    ).map(c => (
                                        <div key={c.code} onClick={() => { setCurrency(c.code); setShowCurrencySearch(false); }}
                                            style={{ padding: "10px", cursor: "pointer", borderBottom: "1px solid #333", color: "#fff", fontSize: "0.85rem", display: "flex", alignItems: "center", gap: "8px" }}>
                                            <span style={{ fontSize: "1.1rem" }}>{getFlagEmoji(c.code.slice(0, 2))}</span>
                                            <span>{c.code} ({c.symbol}) - {c.name}</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                <div className="form-group" style={{ marginBottom: "1.5rem" }}>
                    <label>Patient Phone Number</label>
                    <div style={{ display: "flex", gap: "10px", position: "relative" }}>
                        <div className="input-icon-wrapper" style={{ width: "120px", height: "45px" }}>
                            <i className="fas fa-globe"></i>
                            <input
                                type="text"
                                placeholder="Code"
                                value={countryCode}
                                onChange={(e) => {
                                    setCountryCode(e.target.value);
                                    setShowCountrySearch(true);
                                }}
                                onFocus={() => setShowCountrySearch(true)}
                                className="dashboard-input"
                                style={{ width: "100%", height: "100%" }}
                            />
                            {showCountrySearch && (
                                <div className="elegant-scroll" style={{
                                    position: "absolute", top: "100%", left: 0, right: 0,
                                    zIndex: 105, background: "#1a1a1a", border: "1px solid #444",
                                    borderRadius: "8px", marginTop: "5px", maxHeight: "200px",
                                    overflowY: "auto", boxShadow: "0 10px 25px rgba(0,0,0,0.5)", width: "220px"
                                }}>
                                    {COUNTRY_CODES
                                        .filter(c =>
                                            c.code.includes(countryCode) ||
                                            c.iso.toLowerCase().includes(countryCode.toLowerCase()) ||
                                            c.name.toLowerCase().includes(countryCode.toLowerCase())
                                        )
                                        .map(c => (
                                            <div
                                                key={c.iso}
                                                onClick={() => {
                                                    setCountryCode(c.code);
                                                    setShowCountrySearch(false);
                                                }}
                                                style={{ padding: "10px", cursor: "pointer", borderBottom: "1px solid #333", color: "#fff", fontSize: "0.85rem", display: "flex", alignItems: "center", gap: "8px" }}
                                                onMouseEnter={e => e.currentTarget.style.background = "#2a2a2a"}
                                                onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                                            >
                                                <span style={{ fontSize: "1.2rem" }}>{getFlagEmoji(c.iso)}</span>
                                                <span>{c.name} ({c.code})</span>
                                            </div>
                                        ))
                                    }
                                </div>
                            )}
                            {showCountrySearch && (
                                <div
                                    style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, zIndex: 104 }}
                                    onClick={() => setShowCountrySearch(false)}
                                ></div>
                            )}
                        </div>
                        <input
                            type="text"
                            placeholder="Phone number"
                            value={patientPhone}
                            onChange={(e) => setPatientPhone(e.target.value)}
                            className="dashboard-input"
                            style={{ flex: 1, height: "45px" }}
                        />
                    </div>
                </div>


                {/* Treatment Items */}
                <div className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1.5rem', marginBottom: '0.5rem' }}>
                    <h4>Treatment Details</h4>
                    <button type="button" onClick={addItem} className="action-btn-mini">
                        <i className="fas fa-plus"></i> Add another treatment
                    </button>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '2.5fr 1fr 1fr 1fr 40px', gap: '15px', marginBottom: '5px', padding: '0 10px', fontSize: '0.75rem', fontFamily: 'var(--font-body), Inter, sans-serif', color: '#888', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '1px', alignItems: 'center' }}>
                    <div style={{ paddingLeft: '2px' }}>Treatment</div>
                    <div style={{ paddingLeft: '2px' }}>Cost</div>
                    <div style={{ paddingLeft: '2px' }}>Disc.</div>
                    <div style={{ paddingLeft: '2px' }}>Date</div>
                    <div></div>
                </div>

                {items.map((item, idx) => (
                    <div key={idx} className="dynamic-row" style={{ display: 'grid', gridTemplateColumns: '2.5fr 1fr 1fr 1fr 40px', gap: '15px', marginBottom: '8px', background: 'rgba(34, 34, 34, 0.6)', padding: '8px 12px', borderRadius: '10px', alignItems: 'center' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', position: 'relative' }}>
                            <div style={{ position: 'relative' }}>
                                <input
                                    type="text"
                                    placeholder="Search treatment..."
                                    value={activeTreatmentIdx === idx ? treatmentSearchTerm : item.treatment_name}
                                    onChange={(e) => {
                                        setTreatmentSearchTerm(e.target.value);
                                        setActiveTreatmentIdx(idx);
                                        if (item.treatment_name) updateItem(idx, 'treatment_name', ""); // Reset selection
                                    }}
                                    onFocus={() => {
                                        setTreatmentSearchTerm(item.treatment_name || "");
                                        setActiveTreatmentIdx(idx);
                                    }}
                                    className="dashboard-input"
                                    style={{ paddingLeft: '45px' }}
                                />
                                <i className="fas fa-search" style={{ position: 'absolute', left: '15px', top: '50%', transform: 'translateY(-50%)', color: '#f0b800', opacity: 0.7 }}></i>
                            </div>

                            {activeTreatmentIdx === idx && (treatmentSearchTerm.trim() !== "" || catalog.length > 0) && (
                                <div className="treatment-suggestions elegant-scroll" style={{
                                    position: "absolute", top: "100%", left: 0, right: 0,
                                    zIndex: 102, background: "#1a1a1a", border: "1px solid #444",
                                    borderRadius: "8px", marginTop: "5px", maxHeight: "180px",
                                    overflowY: "auto", boxShadow: "0 10px 25px rgba(0,0,0,0.5)"
                                }}>
                                    {catalog
                                        .filter(cat => cat.name.toLowerCase().includes(treatmentSearchTerm.toLowerCase()))
                                        .map((cat) => (
                                            <div
                                                key={cat.id}
                                                onClick={() => {
                                                    updateItem(idx, 'treatment_name', cat.name);
                                                    setTreatmentSearchTerm(cat.name);
                                                    setActiveTreatmentIdx(null);
                                                }}
                                                style={{
                                                    padding: "10px 15px", cursor: "pointer", borderBottom: "1px solid #333",
                                                    background: item.treatment_name === cat.name ? "#2a2a2a" : "transparent"
                                                }}
                                                onMouseEnter={(e) => e.currentTarget.style.background = "#2a2a2a"}
                                                onMouseLeave={(e) => e.currentTarget.style.background = item.treatment_name === cat.name ? "#2a2a2a" : "transparent"}
                                            >
                                                <div style={{ fontWeight: "600", color: "#fff" }}>{cat.name}</div>
                                                <div style={{ fontSize: "0.75rem", color: "#f0b800" }}>{currencySymbol} {convertPrice(cat.cost, 'INR', currency)}</div>
                                            </div>
                                        ))}
                                    <div
                                        onClick={() => {
                                            updateItem(idx, 'treatment_name', "Other");
                                            setActiveTreatmentIdx(null);
                                        }}
                                        style={{ padding: "10px 15px", cursor: "pointer", color: "#f0b800", fontStyle: "italic" }}
                                    >
                                        + Add Other / Custom
                                    </div>
                                </div>
                            )}

                            {activeTreatmentIdx === idx && (
                                <div
                                    style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, zIndex: 101 }}
                                    onClick={() => setActiveTreatmentIdx(null)}
                                ></div>
                            )}

                            {item.treatment_name === "Other" && (
                                <input
                                    placeholder="Enter Custom Treatment Name"
                                    value={item.custom_name || ""}
                                    onChange={(e) => updateItem(idx, 'custom_name', e.target.value)}
                                    className="dashboard-input"
                                    style={{ marginTop: '5px' }}
                                    required
                                />
                            )}
                        </div>
                        <div style={{ position: 'relative' }}>
                            <input
                                type="number"
                                placeholder="Cost"
                                value={item.cost || ""}
                                onChange={(e) => updateItem(idx, 'cost', e.target.value)}
                                className="dashboard-input"
                                required
                            />
                        </div>
                        <div style={{ position: 'relative' }}>
                            <input
                                type="number"
                                placeholder="Disc."
                                value={item.discount || ""}
                                onChange={(e) => updateItem(idx, 'discount', e.target.value)}
                                className="dashboard-input"
                                style={{ paddingRight: '50px' }}
                            />
                            <select
                                value={item.discount_type}
                                onChange={(e) => updateItem(idx, 'discount_type', e.target.value)}
                                style={{
                                    position: 'absolute',
                                    right: '4px',
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    width: '42px',
                                    background: '#333',
                                    border: 'none',
                                    borderRadius: '6px',
                                    color: '#f0b800',
                                    fontSize: '0.75rem',
                                    height: '30px',
                                    cursor: 'pointer',
                                    outline: 'none',
                                    textAlign: 'center'
                                }}
                            >
                                <option value="flat">{currencySymbol}</option>
                                <option value="percent">%</option>
                            </select>
                        </div>
                                <div className="input-icon-wrapper" style={{ flex: 1, height: "45px" }}>
                                    <i
                                        className="fas fa-calendar-alt"
                                        onClick={(e) => {
                                            const input = e.currentTarget.parentElement.querySelector('input');
                                            if (input) input.showPicker();
                                        }}
                                        style={{ cursor: 'pointer', pointerEvents: 'auto' }}
                                    ></i>
                                    <input
                                        type="date"
                                        value={item.treatment_date}
                                        onChange={(e) => updateItem(idx, "treatment_date", e.target.value)}
                                        className="dashboard-input"
                                        style={{ colorScheme: "dark", width: "100%", height: "100%" }}
                                        onClick={(e) => e.target.showPicker()}
                                    />
                                </div>
                        <button type="button" onClick={() => removeItem(idx)} disabled={items.length === 1} className="trash-btn" style={{ background: 'transparent', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%', height: '100%' }}>
                            <i className="fas fa-trash"></i>
                        </button>
                    </div>
                ))}

                {/* Payments */}
                <div className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1.5rem', marginBottom: '0.5rem' }}>
                    <h4>Payment Records</h4>
                    <button type="button" onClick={addPayment} className="action-btn-mini">
                        <i className="fas fa-plus"></i> Add Payment Item
                    </button>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '2.5fr 1fr 1fr 1fr 40px', gap: '15px', marginBottom: '5px', padding: '0 10px', fontSize: '0.75rem', fontFamily: 'var(--font-body), Inter, sans-serif', color: '#f0b800', fontWeight: 'bold', textTransform: 'uppercase', letterSpacing: '1px', alignItems: 'center' }}>
                    <div style={{ paddingLeft: '2px' }}>Method</div>
                    <div style={{ paddingLeft: '2px' }}>Amount</div>
                    <div style={{ paddingLeft: '2px', gridColumn: '3 / 5' }}>Payment Date</div>
                    <div></div>
                </div>

                {payments.map((p, pIdx) => (
                    <div key={pIdx} className="dynamic-row" style={{ display: 'grid', gridTemplateColumns: '2.5fr 1fr 1fr 1fr 40px', gap: '15px', marginBottom: '8px', background: 'rgba(34, 34, 34, 0.6)', padding: '8px 12px', borderRadius: '10px', alignItems: 'center' }}>
                        <select
                            value={p.payment_method}
                            onChange={(e) => updatePayment(pIdx, 'payment_method', e.target.value)}
                            className="dashboard-select"
                        >
                            <option value="UPI">UPI</option>
                            <option value="Cash">Cash</option>
                            <option value="Card">Card</option>
                            <option value="Bank Transfer">Bank Transfer</option>
                            <option value="Paytm">Paytm</option>
                        </select>
                        <div style={{ position: 'relative' }}>
                            <input
                                type="number"
                                placeholder="Amount"
                                value={p.amount || ""}
                                onChange={(e) => updatePayment(pIdx, 'amount', e.target.value)}
                                className="dashboard-input"
                            />
                            <span style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', opacity: 0.5, fontSize: '0.8rem' }}>{currencySymbol}</span>
                        </div>
                                <div className="input-icon-wrapper" style={{ flex: 1, height: "45px" }}>
                                    <i
                                        className="fas fa-calendar-alt"
                                        onClick={(e) => {
                                            const input = e.currentTarget.parentElement.querySelector('input');
                                            if (input) input.showPicker();
                                        }}
                                        style={{ cursor: 'pointer', pointerEvents: 'auto' }}
                                    ></i>
                                    <input
                                        type="date"
                                        value={p.paid_on}
                                        onChange={(e) => updatePayment(pIdx, "paid_on", e.target.value)}
                                        className="dashboard-input"
                                        style={{ colorScheme: "dark", width: "100%", height: "100%" }}
                                        onClick={(e) => e.target.showPicker()}
                                    />
                                </div>
                        <button type="button" onClick={() => removePayment(pIdx)} disabled={payments.length === 1} style={{ background: 'transparent', color: '#ff4444', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%', height: '100%' }}>
                            <i className="fas fa-trash"></i>
                        </button>
                    </div>
                ))}

                {/* Summary */}
                {/* Summary */}
                <div className="invoice-summary">
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                        <span>Subtotal (Gross):</span>
                        <span style={{ fontWeight: 'bold' }}>{currencySymbol} {subtotal.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </div>

                    {totalItemDiscount > 0 && (
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px', color: '#f0b800' }}>
                            <span>Total Item Discounts:</span>
                            <span style={{ fontWeight: 'bold' }}>- {currencySymbol} {totalItemDiscount.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                        </div>
                    )}

                    <div className="total-row" style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 'bold' }}>
                        <span>Total Payable:</span>
                        <span>{currencySymbol} {totalAmount.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', color: '#2ecc71', marginTop: '8px', fontSize: '0.9rem', opacity: 0.8 }}>
                        <span>Total Paid:</span>
                        <span>{currencySymbol} {totalPaid.toLocaleString("en-IN")}</span>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', color: amountDue > 0 ? '#ff7675' : '#2ecc71', fontWeight: 'bold', marginTop: '8px' }}>
                        <span>{amountDue > 0 ? "Amount Due:" : "Balance Cleared"}</span>
                        <span>{currencySymbol} {Math.abs(amountDue).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </div>
                </div>

                <button
                    type="submit"
                    disabled={isSubmitting}
                    className="upload-btn"
                >
                    {isSubmitting ? <span className="fas fa-spinner fa-spin"></span> : <i className={editingInvoice ? "fas fa-save" : "fas fa-file-invoice"}></i>}
                    {isSubmitting ? (editingInvoice ? " Updating..." : " Generating...") : (editingInvoice ? " Update Invoice" : " Generate & Save Invoice")}
                </button>
            </form>
        </div>
    );
};

export default InvoiceForm;
