export function WindArt({ small = false }: { small?: boolean }) {
  return (
    <svg
      className={`wind-art ${small ? "small" : ""}`}
      viewBox="0 0 1440 500"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={small ? "wind-small" : "wind-wide"}>
          <stop stopColor="#008da8" stopOpacity="0" />
          <stop offset=".3" stopColor="#087fcb" />
          <stop offset=".6" stopColor="#8159ef" />
          <stop offset=".85" stopColor="#22bdcf" />
          <stop offset="1" stopColor="#8769f9" stopOpacity=".1" />
        </linearGradient>
      </defs>
      {Array.from({ length: 26 }, (_, i) => (
        <path
          key={i}
          d={`M -80 ${260 + i * 4} C 150 ${450 - i * 6}, 230 ${10 + i * 4}, 440 ${115 + i * 6} S 660 ${390 - i * 4}, 850 ${230 + i * 4} S 1080 ${50 - i * 5}, 1520 ${110 + i * 10}`}
          fill="none"
          stroke={`url(#${small ? "wind-small" : "wind-wide"})`}
          strokeWidth={i % 5 === 0 ? 1.1 : 0.55}
          opacity={i % 4 === 0 ? 0.8 : 0.35}
        />
      ))}
      {Array.from({ length: 30 }, (_, i) => (
        <circle
          key={i}
          cx={(i * 179) % 1440}
          cy={(i * 83) % 480}
          r={i % 3 === 0 ? 1.5 : 0.8}
          fill={i % 2 ? "#55dbe1" : "#a393fc"}
          opacity=".5"
        />
      ))}
    </svg>
  );
}
