export default function Footer() {
  return (
    <footer className="bg-[#0f0f0f] border-t border-white/[0.06] py-8 px-6">
      <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <img
            src="/static/assets/logo.png"
            alt="Smile Artists"
            className="w-8 h-8 rounded-full border border-[#d4af37]/40 object-cover"
          />
          <span
            className="text-white/70 text-sm"
            style={{ fontFamily: "'Playfair Display', serif" }}
          >
            Smile Artists Dental Studio
          </span>
        </div>

        {/* Socials */}
        <div className="flex items-center gap-4">
          <a
            href="https://www.facebook.com/smileartistsdentalstudio"
            target="_blank"
            rel="noopener noreferrer"
            className="w-9 h-9 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-white/50 hover:text-[#d4af37] hover:border-[#d4af37]/40 transition-all duration-200 no-underline"
          >
            <i className="fab fa-facebook text-sm" />
          </a>
          <a
            href="https://www.instagram.com/smileartistsdentalstudio"
            target="_blank"
            rel="noopener noreferrer"
            className="w-9 h-9 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-white/50 hover:text-[#d4af37] hover:border-[#d4af37]/40 transition-all duration-200 no-underline"
          >
            <i className="fab fa-instagram text-sm" />
          </a>
        </div>

        {/* Copyright + FlossyAI */}
        <div className="text-center md:text-right">
          <p className="text-white/30 text-xs m-0">© 2023 Smile Artists Dental Studio</p>
          <p className="text-white/20 text-xs mt-0.5 m-0">
            Powered by <span className="text-[#d4af37]/60 font-semibold">FlossyAI</span>
          </p>
        </div>
      </div>
    </footer>
  );
}
