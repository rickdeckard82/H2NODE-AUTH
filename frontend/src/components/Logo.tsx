/**
 * Logotipo do H2NODE Auth (animado). Alterna entre a versão clara e a escura
 * conforme o tema do navegador (prefers-color-scheme). Arquivos em `public/`.
 */
export function Logo({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <>
      <img src="/logo-light.svg" alt="H2NODE Auth" className={`${className} block object-contain dark:hidden`} />
      <img src="/logo-dark.svg" alt="H2NODE Auth" className={`${className} hidden object-contain dark:block`} />
    </>
  );
}
