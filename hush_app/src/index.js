import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { UserProvider } from "./UserContext/userProvider";

// Replace this with your actual Google OAuth Client ID
const clientId = "387653948430-kmg1urmijluvtrbkin3736ffcvbduv9b.apps.googleusercontent.com";

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <UserProvider>
      <GoogleOAuthProvider clientId={clientId}>
        <App />
      </GoogleOAuthProvider>
    </UserProvider>
  </React.StrictMode>
);

reportWebVitals();
