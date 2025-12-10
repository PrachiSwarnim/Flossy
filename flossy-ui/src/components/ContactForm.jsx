export default function ContactForm() {
    return (
      <div className="contact-form-wrapper">
        <h2>Send Us a Message</h2>
  
        <form className="contact-form">
          <input type="text" placeholder="Full Name" required />
          <input type="email" placeholder="Email Address" required />
          <input type="tel" placeholder="Phone Number" required />
          <textarea rows="5" placeholder="Your Message" required />
  
          <button type="submit">Submit</button>
        </form>
      </div>
    );
  }
  