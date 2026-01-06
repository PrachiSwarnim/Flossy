import React, { useState, useEffect } from 'react';
import { useSession } from '@clerk/clerk-react';

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const InvoiceForm = ({ patientsList, onInvoiceCreated }) => {
    const { session } = useSession();
    const [patientName, setPatientName] = useState("");
    const [currency, setCurrency] = useState("INR");
    const [discount, setDiscount] = useState(0);
    const [discountType, setDiscountType] = useState("fixed"); // "fixed" or "percent"
    const [items, setItems] = useState([{ treatment_name: "", cost: 0, treatment_date: new Date().toISOString().split('T')[0] }]);
    const [payments, setPayments] = useState([{ payment_method: "UPI", amount: 0, paid_on: new Date().toISOString().split('T')[0] }]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isManualPayment, setIsManualPayment] = useState(false); // Track if user manually edited payment
    const [catalog, setCatalog] = useState([]);

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

    // Auto-calculate totals
    const subtotal = items.reduce((sum, item) => sum + (parseFloat(item.cost) || 0), 0);

    const discountValue = discountType === "percent"
        ? (subtotal * (parseFloat(discount || 0) / 100))
        : parseFloat(discount || 0);

    const totalAmount = Math.max(0, subtotal - discountValue);
    const totalPaid = payments.reduce((sum, pay) => sum + (parseFloat(pay.amount) || 0), 0);
    const amountDue = totalAmount - totalPaid;

    // Auto-fill payment amount if not manual
    useEffect(() => {
        if (!isManualPayment && payments.length === 1) {
            const newPayments = [...payments];
            newPayments[0].amount = Math.max(0, totalAmount);
            setPayments(newPayments);
        }
    }, [totalAmount, isManualPayment]);

    const addItem = () => {
        setItems([...items, { treatment_name: "", cost: 0, treatment_date: new Date().toISOString().split('T')[0] }]);
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
                newItems[index].cost = match.cost;
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
        setPayments(newPayments);
        if (field === "amount") setIsManualPayment(true);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!patientName) return alert("Please select a patient.");
        if (items.some(it => !it.treatment_name || (it.treatment_name === "Other" && !it.custom_name) || it.cost < 0)) {
            return alert("Please fill all treatment details (including custom names) with valid costs.");
        }

        setIsSubmitting(true);
        try {
            const token = await session.getToken({ template: "default" });
            const res = await fetch(`${API}/api/invoices`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({
                    patient_name: patientName,
                    discount: discountValue, // Send the calculated absolute discount
                    items: items.map(it => ({
                        ...it,
                        treatment_name: it.treatment_name === "Other" ? it.custom_name : it.treatment_name,
                        cost: parseFloat(it.cost)
                    })),
                    payments: payments.map(p => ({ ...p, amount: parseFloat(p.amount) })),
                    currency: currency // Future proofing backend
                })
            });

            if (res.ok) {
                alert("Invoice generated successfully!");
                setPatientName("");
                setDiscount(0);
                setItems([{ treatment_name: "", cost: 0, treatment_date: new Date().toISOString().split('T')[0] }]);
                setPayments([{ payment_method: "UPI", amount: 0, paid_on: new Date().toISOString().split('T')[0] }]);
                setIsManualPayment(false);
                if (onInvoiceCreated) onInvoiceCreated();
            } else {
                const err = await res.json();
                alert("Failed to create invoice: " + (err.detail || "Unknown error"));
            }
        } catch (err) {
            console.error(err);
            alert("Error creating invoice.");
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="invoice-form-container" style={{ color: '#fff' }}>
            <form onSubmit={handleSubmit} className="premium-form">
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                    <div className="form-group">
                        <label style={{ color: '#f0b800', fontWeight: 'bold' }}>Select Patient</label>
                        <select
                            value={patientName}
                            onChange={(e) => setPatientName(e.target.value)}
                            className="dashboard-select"
                            required
                        >
                            <option value="">-- Choose Patient --</option>
                            {patientsList.map(p => (
                                <option key={p.id} value={p.name}>{p.name}</option>
                            ))}
                        </select>
                    </div>
                    <div className="form-group">
                        <label style={{ color: '#f0b800', fontWeight: 'bold' }}>Currency</label>
                        <select
                            value={currency}
                            onChange={(e) => setCurrency(e.target.value)}
                            className="dashboard-select"
                        >
                            <option value="INR">INR (₹)</option>
                            <option value="USD">USD ($)</option>
                            <option value="EUR">EUR (€)</option>
                            <option value="GBP">GBP (£)</option>
                            <option value="AED">AED</option>
                        </select>
                    </div>
                </div>

                {/* Treatment Items */}
                <div className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1.5rem', marginBottom: '0.5rem' }}>
                    <h4 style={{ color: '#f0b800' }}>Treatment Details</h4>
                    <button type="button" onClick={addItem} className="action-btn-mini" style={{ background: '#f0b800', color: '#000', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
                        <i className="fas fa-plus"></i> Add another treatment
                    </button>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 40px', gap: '10px', marginBottom: '5px', padding: '0 10px', fontSize: '0.8rem', color: '#888', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    <div>Treatment</div>
                    <div>Cost</div>
                    <div>Treatment Date</div>
                    <div></div>
                </div>

                {items.map((item, idx) => (
                    <div key={idx} className="dynamic-row" style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 40px', gap: '10px', marginBottom: '10px', background: '#222', padding: '10px', borderRadius: '8px', alignItems: 'flex-start' }}>
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <select
                                value={item.treatment_name}
                                onChange={(e) => updateItem(idx, 'treatment_name', e.target.value)}
                                className="dashboard-select"
                                required
                            >
                                <option value="">-- Select Treatment --</option>
                                {catalog.map(cat => (
                                    <option key={cat.id} value={cat.name}>
                                        {cat.name}
                                    </option>
                                ))}
                                <option value="Other">Other / Custom</option>
                            </select>
                            {item.treatment_name === "Other" && (
                                <input
                                    placeholder="Treatment Name"
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
                            <span style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', opacity: 0.5, fontSize: '0.8rem' }}>{currency}</span>
                        </div>
                        <input
                            type="date"
                            value={item.treatment_date}
                            onChange={(e) => updateItem(idx, 'treatment_date', e.target.value)}
                            className="dashboard-input"
                        />
                        <button type="button" onClick={() => removeItem(idx)} disabled={items.length === 1} style={{ background: 'transparent', color: '#ff4444', border: 'none', cursor: 'pointer' }}>
                            <i className="fas fa-trash"></i>
                        </button>
                    </div>
                ))}

                {/* Payments */}
                <div className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1.5rem', marginBottom: '0.5rem' }}>
                    <h4 style={{ color: '#f0b800' }}>Payment Records</h4>
                    <button type="button" onClick={addPayment} className="action-btn-mini" style={{ background: '#f0b800', color: '#000', border: 'none', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer' }}>
                        <i className="fas fa-plus"></i> Add Payment Item
                    </button>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 40px', gap: '10px', marginBottom: '5px', padding: '0 10px', fontSize: '0.8rem', color: '#888', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    <div>Method</div>
                    <div>Amount</div>
                    <div>Payment Date</div>
                    <div></div>
                </div>

                {payments.map((p, idx) => (
                    <div key={idx} className="dynamic-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 40px', gap: '10px', marginBottom: '10px', background: '#222', padding: '10px', borderRadius: '8px' }}>
                        <select
                            value={p.payment_method}
                            onChange={(e) => updatePayment(idx, 'payment_method', e.target.value)}
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
                                onChange={(e) => updatePayment(idx, 'amount', e.target.value)}
                                className="dashboard-input"
                            />
                            <span style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', opacity: 0.5, fontSize: '0.8rem' }}>{currency}</span>
                        </div>
                        <input
                            type="date"
                            value={p.paid_on}
                            onChange={(e) => updatePayment(idx, 'paid_on', e.target.value)}
                            className="dashboard-input"
                        />
                        <button type="button" onClick={() => removePayment(idx)} disabled={payments.length === 1} style={{ background: 'transparent', color: '#ff4444', border: 'none', cursor: 'pointer' }}>
                            <i className="fas fa-trash"></i>
                        </button>
                    </div>
                ))}

                {/* Summary */}
                <div className="invoice-summary" style={{ marginTop: '1.5rem', padding: '15px', background: '#1a1a1a', borderRadius: '10px', border: '1px solid #333' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <span>Gross Amount:</span>
                        <span style={{ fontWeight: 'bold' }}>{currency} {subtotal.toLocaleString()}</span>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', alignItems: 'center' }}>
                        <span>Discount:</span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <select
                                value={discountType}
                                onChange={(e) => setDiscountType(e.target.value)}
                                className="dashboard-select"
                                style={{ width: 'auto', height: '32px', padding: '0 8px', minWidth: '60px' }}
                            >
                                <option value="fixed">{currency}</option>
                                <option value="percent">%</option>
                            </select>
                            <input
                                type="number"
                                value={discount || ""}
                                onChange={(e) => setDiscount(e.target.value)}
                                className="dashboard-input"
                                style={{ width: '80px', height: '32px', textAlign: 'right' }}
                                placeholder="0"
                            />
                        </div>
                    </div>

                    <hr style={{ borderColor: '#333', margin: '10px 0' }} />

                    <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 'bold', fontSize: '1.1rem', color: '#f0b800', marginTop: '5px' }}>
                        <span>Total Amount:</span>
                        <span>{currency} {totalAmount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', color: '#2ecc71', marginTop: '5px', fontSize: '0.9rem' }}>
                        <span>Total Paid:</span>
                        <span>{currency} {totalPaid.toLocaleString()}</span>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', color: amountDue > 0 ? '#ff4444' : '#2ecc71', fontWeight: 'bold', marginTop: '5px' }}>
                        <span>{amountDue > 0 ? "Amount Due:" : "Balance Cleared"}</span>
                        <span>{currency} {Math.abs(amountDue).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                    </div>
                </div>

                <button
                    type="submit"
                    disabled={isSubmitting}
                    className="upload-btn"
                    style={{ width: '100%', marginTop: '1.5rem', background: '#f0b800', color: '#000', fontWeight: 'bold', padding: '12px' }}
                >
                    {isSubmitting ? <i className="fas fa-spinner fa-spin"></i> : <i className="fas fa-file-invoice"></i>}
                    {isSubmitting ? " Generating..." : " Generate & Save Invoice"}
                </button>
            </form>
        </div>
    );
};

export default InvoiceForm;
