import { motion } from "framer-motion";

export default function Team() {
  const team = [
    {
      name: "Dr. Shagufta Jawaid",
      img: "/static/assets/Dr Shagufta Jawaid.avif",
      desc: "A compassionate and skilled dentist, Dr. Jawaid is known for her patient-first approach and dedication to advanced dental technologies.",
      link: "https://www.linkedin.com/in/dr-shagufta-jawaid-53604b203/"
    },
    {
      name: "Dr. Shruti Choudhary",
      img: "/static/assets/Dr Shruti Choudhary.avif",
      desc: "With her gentle and friendly approach, Dr. Choudhary makes dental care stress-free and enjoyable while ensuring precision and comfort.",
      link: "https://www.linkedin.com/in/shruti-choudhary01/"
    },
    {
      name: "Dr. Aishwarya Singh",
      img: "/static/assets/Dr Aishwarya Singh.avif",
      desc: "An expert in smile design, Dr. Singh's artistry and attention to detail bring out radiant, confident smiles with every treatment.",
      link: "https://www.linkedin.com/company/wix-com/"
    }
  ];

  return (
    <section className="bg-[#151515] pt-16 pb-8 px-6 md:px-[8%]">
      <div className="max-w-5xl mx-auto text-center mb-12">
        <motion.h2
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          viewport={{ once: true }}
          className="text-[2.2rem] mb-3 text-white"
          style={{ fontFamily: "'Playfair Display', serif" }}
        >
          Meet the <span className="text-[#d4af37]">Team</span>
        </motion.h2>
        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          viewport={{ once: true }}
          className="text-white/50 max-w-xl mx-auto text-sm leading-relaxed"
        >
          The Smile Artists team is built on friendship, expertise, and empathy —
          three dentists united by a shared passion for creating brighter, healthier smiles.
        </motion.p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
        {team.map((t, i) => (
          <motion.div
            key={t.name}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.15, duration: 0.5 }}
            viewport={{ once: true }}
            whileHover={{ y: -6 }}
            className="group bg-[#1a1a1a] rounded-2xl overflow-hidden border border-white/5 hover:border-[#d4af37]/30 transition-all duration-300 shadow-[0_10px_40px_rgba(0,0,0,0.4)] hover:shadow-[0_16px_50px_rgba(212,175,55,0.1)]"
          >
            <div className="relative overflow-hidden h-64">
              <img
                src={t.img}
                alt={t.name}
                className="w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-500"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[#1a1a1a] via-transparent to-transparent" />
            </div>

            <div className="p-6">
              <h3
                className="text-white text-lg mb-2"
                style={{ fontFamily: "'Playfair Display', serif" }}
              >
                {t.name}
              </h3>
              <p className="text-white/50 text-sm leading-relaxed mb-4">{t.desc}</p>
              <a
                href={t.link}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-[#d4af37] hover:text-white text-sm font-medium transition-colors duration-200 no-underline"
              >
                <i className="fab fa-linkedin text-base" />
                <span>LinkedIn</span>
              </a>
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
