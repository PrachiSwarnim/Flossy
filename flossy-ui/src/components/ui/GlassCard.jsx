import React from "react";
import { motion } from "framer-motion";

export const GlassCard = ({ children, className = "", containerStyle = {} }) => {
    return (
        <motion.div
            initial={{ opacity: 0, y: 30, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{
                duration: 0.8,
                ease: [0.25, 0.46, 0.45, 0.94]
            }}
            whileHover={{
                scale: 1.02,
                boxShadow: "0 25px 60px rgba(0,0,0,0.6), 0 0 40px rgba(212, 175, 55, 0.3)",
            }}
            style={{
                ...containerStyle,
                transition: "box-shadow 0.4s ease, transform 0.4s ease"
            }}
            className={className}
        >
            {/* Animated border glow */}
            <motion.div
                style={{
                    position: "absolute",
                    inset: -2,
                    borderRadius: "22px",
                    background: "linear-gradient(135deg, rgba(212, 175, 55, 0.4), rgba(212, 175, 55, 0.1), rgba(212, 175, 55, 0.4))",
                    backgroundSize: "200% 200%",
                    zIndex: -1,
                    opacity: 0
                }}
                animate={{
                    backgroundPosition: ["0% 0%", "100% 100%", "0% 0%"],
                    opacity: [0.3, 0.6, 0.3]
                }}
                transition={{
                    duration: 4,
                    repeat: Infinity,
                    ease: "easeInOut"
                }}
            />
            {children}
        </motion.div>
    );
};
