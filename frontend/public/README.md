# Assets públicos

Servidos na raiz do site (ex.: `/logo-light.svg`).

## Logotipo

- `logo-light.svg` — tema claro.
- `logo-dark.svg` — tema escuro.

Logotipo animado do H2NODE Auth (SVG com CSS; respeita `prefers-reduced-motion`).
Os dois arquivos são iguais hoje (o fundo escuro funciona nos dois temas); mantenha-os
separados para poder ajustar um tema sem mexer no outro. `src/components/Logo.tsx`
escolhe pelo tema e também é usado como favicon (`index.html`).
