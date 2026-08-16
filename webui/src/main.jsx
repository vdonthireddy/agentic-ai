import React from 'react';
import ReactDOM from 'react-dom/client';
import { Provider, defaultTheme } from '@adobe/react-spectrum';
import App from './App';
import './styles/index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Provider theme={defaultTheme} colorScheme="dark">
      <App />
    </Provider>
  </React.StrictMode>
);
