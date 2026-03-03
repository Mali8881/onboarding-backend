export default function Kasper({ type = 'happy', size = 100, style = {}, caption = null }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6, flexShrink: 0, ...style }}>
      <video
        src={`/kasper/kasper_${type}.mp4`}
        autoPlay
        loop
        muted
        playsInline
        style={{
          width: size,
          height: size,
          objectFit: 'contain',
          // Пробуем разные blend mode — какой уберёт фон зависит от цвета фона видео
          // Если фон БЕЛЫЙ — multiply убирает его
          // Если фон ЧЁРНЫЙ — screen убирает его
          mixBlendMode: 'screen',
        }}
      />
      {caption && (
        <p style={{ fontSize: 13, color: 'var(--gray-400)', textAlign: 'center', margin: 0 }}>
          {caption}
        </p>
      )}
    </div>
  );
}
