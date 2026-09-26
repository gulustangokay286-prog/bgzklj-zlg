import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App.tsx';
import * as store from './store.ts';
import './app.css';

// Geliştirme sırasında tarayıcı konsolundan durumu okuyabilmek için.
if (import.meta.env.DEV) (window as any).__app = store;

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);
