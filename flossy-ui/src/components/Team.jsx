import "../styles/team.css";

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
      desc: "An expert in smile design, Dr. Singh’s artistry and attention to detail bring out radiant, confident smiles with every treatment.",
      link: "https://www.linkedin.com/company/wix-com/"
    }
  ];

  return (
    <section id="team" className="team-section">
      <h2>Meet the Team</h2>

      <p className="team-intro">
        The Smile Artists team is built on friendship, expertise, and empathy — 
        three dentists united by a shared passion for creating brighter, healthier smiles.
      </p>

      <div className="team-grid">
        {team.map((t) => (
          <div className="member" key={t.name}>
            <img src={t.img} alt={t.name} />
            <h3>{t.name}</h3>
            <p>{t.desc}</p>

            <a href={t.link} target="_blank" rel="noopener noreferrer">
              <i className="fab fa-linkedin"></i>
            </a>
          </div>
        ))}
      </div>
    </section>
  );
}
