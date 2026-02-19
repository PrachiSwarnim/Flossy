/** @type {import('tailwindcss').Config} */
module.exports = {
	content: [
		"./app/**/*.{js,ts,jsx,tsx,mdx}",
		"./pages/**/*.{js,ts,jsx,tsx,mdx}",
		"./components/**/*.{js,ts,jsx,tsx,mdx}",
		"./src/**/*.{js,ts,jsx,tsx,mdx}",
	],
	theme: {
		extend: {
			colors: {
				gold: {
					DEFAULT: "#d4af37",
					light: "#e6be8a",
					hover: "#f3d4a0",
					muted: "#a07830",
				},
				dark: {
					DEFAULT: "#151515",
					deeper: "#111111",
					card: "#1f1f1f",
				},
			},
			fontFamily: {
				heading: ['"Playfair Display"', "serif"],
				body: ["Inter", "sans-serif"],
				brand: ['"Cooper Black"', "serif"],
				tagline: ['"Monotype Corsiva"', "cursive"],
			},
			boxShadow: {
				gold: "0 4px 15px rgba(212,175,55,0.25)",
				"gold-lg": "0 8px 30px rgba(212,175,55,0.35)",
				card: "0 10px 40px rgba(0,0,0,0.5)",
			},
			animation: {
				spotlight: "spotlight 2s ease .75s 1 forwards",
				"meteor-effect": "meteor 5s linear infinite",
				"fade-up": "fadeInUp 0.6s ease-out forwards",
				float: "float 6s ease-in-out infinite",
			},
			keyframes: {
				spotlight: {
					"0%": { opacity: 0, transform: "translate(-72%, -62%) scale(0.5)" },
					"100%": { opacity: 1, transform: "translate(-50%,-40%) scale(1)" },
				},
				meteor: {
					"0%": { transform: "rotate(215deg) translateX(0)", opacity: "1" },
					"70%": { opacity: "1" },
					"100%": { transform: "rotate(215deg) translateX(-500px)", opacity: "0" },
				},
				fadeInUp: {
					from: { opacity: 0, transform: "translateY(24px)" },
					to: { opacity: 1, transform: "translateY(0)" },
				},
				float: {
					"0%, 100%": { transform: "translateY(0px)" },
					"50%": { transform: "translateY(-10px)" },
				},
			},
		},
	},
	plugins: [],
};