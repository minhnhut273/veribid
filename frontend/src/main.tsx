import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { Amplify } from 'aws-amplify';
import './styles.css';
import { App } from './App';

const userPoolId = import.meta.env.VITE_USER_POOL_ID as string | undefined;
const userPoolClientId = import.meta.env.VITE_USER_POOL_CLIENT_ID as string | undefined;
if (userPoolId && userPoolClientId) {
  Amplify.configure({ Auth: { Cognito: { userPoolId, userPoolClientId, loginWith: { email: true } } } });
}

createRoot(document.getElementById('root')!).render(
  <StrictMode><App /></StrictMode>,
);
