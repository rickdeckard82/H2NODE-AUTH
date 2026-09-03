import type { SyntheticEvent } from "react";

/**
 * Logotipo do Pulse RADIUS. Alterna entre a versão clara e a escura conforme o
 * tema do navegador (prefers-color-scheme). Arquivos em `public/`:
 *   - logo-light.(png|svg)  → tema claro (logo colorido)
 *   - logo-dark.(png|svg)   → tema escuro (logo claro/branco)
 * Usa .png se existir; senão cai no .svg (placeholder incluído no repo).
 */
function fallbackToSvg(e: SyntheticEvent<HTMLImageElement>) {
  const img = e.currentTarget;
  if (img.src.endsWith(".png")) img.src = img.src.replace(/\.png$/, ".svg");
}

export function Logo({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <>
      <img
        src="/logo-light.png"
        alt="Pulse RADIUS"
        onError={fallbackToSvg}
        className={`${className} block object-contain dark:hidden`}
      />
      <img
        src="/logo-dark.png"
        alt="Pulse RADIUS"
        onError={fallbackToSvg}
        className={`${className} hidden object-contain dark:block`}
      />
    </>
  );
}
