import { useEffect } from "react";
import { motion, useAnimation } from "framer-motion";
import { useInView } from "framer-motion";
import { useRef } from "react";

export const TextGenerateEffect = ({ words, className = "" }) => {
    const scope = useRef(null);
    const isInView = useInView(scope);
    const controls = useAnimation();

    const wordsArray = words.split(" ");

    useEffect(() => {
        if (isInView) {
            controls.start({
                opacity: 1,
                filter: "blur(0px)",
                transition: {
                    duration: 1,
                    delay: 0.2,
                },
            });
        }
    }, [isInView, controls]);

    return (
        <div ref={scope} className={className}>
            <motion.div>
                {wordsArray.map((word, idx) => {
                    return (
                        <motion.span
                            key={word + idx}
                            initial={{ opacity: 0, filter: "blur(10px)" }}
                            animate={controls}
                            transition={{
                                duration: 0.5,
                                delay: idx * 0.1,
                            }}
                            style={{
                                display: "inline-block",
                                marginRight: "0.2em",
                            }}
                        >
                            {word}
                        </motion.span>
                    );
                })}
            </motion.div>
        </div>
    );
};
