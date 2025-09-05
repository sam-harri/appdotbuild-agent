# Vue.js Application Template

This is a Vue.js 3 application that replicates the functionality and design of the original React application.

## Features

- **Vue 3** with Composition API
- **TypeScript** support
- **Tailwind CSS** for styling
- **PrimeVue** component library
- **Vite** for fast development and building
- **Same visual design** as the original React app
- **API utilities** for backend communication

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm, yarn, or pnpm

### Installation

1. Install dependencies:
```bash
npm install
# or
yarn install
# or
pnpm install
```

2. Start development server:
```bash
npm run dev
# or
yarn dev
# or
pnpm dev
```

3. Open your browser and navigate to `http://localhost:3000`

### Building for Production

```bash
npm run build
# or
yarn build
# or
pnpm build
```

## Project Structure

```
client2/
├── src/
│   ├── components/          # Vue components
│   ├── utils/
│   │   └── api.ts         # API utilities (same as React app)
│   ├── App.vue            # Main application component
│   ├── main.ts            # Application entry point
│   └── index.css          # Global styles with Tailwind
├── public/                 # Static assets
├── index.html             # HTML template
├── vite.config.ts         # Vite configuration
├── tailwind.config.js     # Tailwind CSS configuration
├── tsconfig.json          # TypeScript configuration
└── package.json           # Dependencies and scripts
```

## Key Differences from React Version

- Uses Vue 3 Composition API instead of React hooks
- PrimeVue components instead of Radix UI
- Vue Single File Components (.vue files) instead of JSX
- Same API structure and visual design
- Same Tailwind CSS styling approach

## Component Library

This project uses **PrimeVue**, one of the most popular Vue.js component libraries. All PrimeVue components are globally available and styled with the default theme.

## API Integration

The `src/utils/api.ts` file maintains the same structure as the React version, making it easy to integrate with existing backend services.

## Styling

- **Tailwind CSS** for utility-first styling
- **CSS Custom Properties** for theming
- **Responsive design** with mobile-first approach
- **Dark mode support** via CSS media queries

## Development

- **Hot Module Replacement** for fast development
- **TypeScript** for type safety
- **ESLint** for code quality
- **Vite** for fast builds and development server
