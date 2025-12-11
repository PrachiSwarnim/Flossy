import "../styles/footer.css";

export default function Footer() {
  return (
    <footer className="footer">
      <div className="footer-row">
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

        <span className="footer-copyright">
          © 2023 Smile Artists Dental Studio
        </span>
      </div>

      <div className="footer-powered">
        Powered by FlossyAI
      </div>
    </footer>
  );
}
