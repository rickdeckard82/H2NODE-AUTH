# Assets públicos

Servidos na raiz do site (ex.: `/logo-light.svg`).

## Logotipo

- `logo-light.svg` — usado no **tema claro** (versão colorida do logo).
- `logo-dark.svg` — usado no **tema escuro** (versão clara/branca do logo).

Os `.svg` aqui são **placeholders**. Para usar os logos oficiais, salve-os como:

- `frontend/public/logo-light.png` — versão colorida (tema claro)
- `frontend/public/logo-dark.png` — versão clara/branca (tema escuro)

`src/components/Logo.tsx` tenta o `.png` e, se não existir, cai no `.svg`.
Recomendado: quadrado com margem interna, ~256–512 px (PNG com fundo transparente).
