import "../styles/footer.css";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-socials">
        <a 
          href="https://www.facebook.com/smileartistsdentalstudio" 
          target="_blank" 
          rel="noopener noreferrer"
        >
          <i className="fab fa-facebook"></i>
        </a>

        <a 
          href="https://www.instagram.com/smileartistsdentalstudio" 
          target="_blank" 
          rel="noopener noreferrer"
        >
          <i className="fab fa-instagram"></i>
        </a>
      </div>

      <p className="footer-text">
        © 2023 Smile Artists Dental Studio | Powered by FlossyAI
      </p>
    </footer>
  );
}
