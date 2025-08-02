import React, { useState, useContext } from "react";
import { Button, Form } from "react-bootstrap";
import { useNavigate } from "react-router-dom";
import "bootstrap/dist/css/bootstrap.min.css";
import "../styles/Auth.css";
import "../styles/Splash.css";
import Image from "../assets/Brand_logo.png";
import { GoogleLogin } from '@react-oauth/google';
import axios from 'axios';
import UserContext from "../UserContext/userContext";
import { toast } from 'react-toastify';

function SignIn() {
  const navigate = useNavigate();
  const { setUser } = useContext(UserContext);
  
  // State for the email/password form
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });

  const handleInputChange = (e) => {
    const { id, value } = e.target;
    setFormData(prev => ({ ...prev, [id]: value }));
  };

  // --- Google Sign-In Logic ---
  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      const res = await axios.post("http://localhost:8000/auth/google", {
        token: credentialResponse.credential
      });
      
      const { exists, idinfo, consent_token, user_data } = res.data;

      if (exists) {
        toast.success(`🎉 Welcome back, ${user_data.name}!`);
        setUser({
          name: user_data.name,
          email: user_data.email,
          consentToken: consent_token,
        });
        navigate("/home");
      } else {
        toast.info("Welcome! Please complete your profile to continue.");
        setUser({
            name: idinfo.name,
            email: idinfo.email,
            consentToken: consent_token
        });
        navigate("/FormSignup");
      }
    } catch (err) {
      console.error("Authentication failed:", err);
      toast.error("Authentication failed. Please try again.");
    }
  };

  // --- Email/Password Sign-In Logic ---
  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await axios.post("http://localhost:8000/api/signin-email", {
        email: formData.email,
        password: formData.password
      });

      const { user_data, consent_token } = res.data;

      toast.success(`🎉 Welcome back, ${user_data.name}!`);
      setUser({
        name: user_data.name,
        email: user_data.email,
        consentToken: consent_token,
      });
      navigate("/home");

    } catch (error) {
      if (error.response && error.response.status === 401) {
        toast.error("Invalid email or password.");
      } else {
        toast.error("Login failed. Please try again.");
      }
      console.error("Signin failed:", error);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <img className="brand-image d-block mx-auto mb-3" src={Image} alt="Brand Logo" />
          <h3 className="auth-title">Welcome Back</h3>
          <h4 className="auth-subtitle">Sign In to continue</h4>
        </div>

        <div className="google-btn-wrapper w-100 my-3">
          <GoogleLogin
            onSuccess={handleGoogleSuccess}
            onError={() => toast.error("Google login failed.")}
            useOneTap theme="filled_black" text="continue_with" shape="rectangular"
          />
        </div>

        <div className="divider">
          <hr className="flex-grow-1" />
          <span className="px-2 text-white fw-lighter">or</span>
          <hr className="flex-grow-1" />
        </div>

        <Form onSubmit={handleSubmit}>
          <Form.Group className="mb-3" controlId="email">
            <Form.Label className="labels">Email address</Form.Label>
            <Form.Control type="email" placeholder="Enter email" required onChange={handleInputChange} value={formData.email} />
          </Form.Group>
          <Form.Group className="mb-4" controlId="password">
            <Form.Label className="labels">Password</Form.Label>
            <Form.Control type="password" placeholder="Password" required onChange={handleInputChange} value={formData.password}/>
          </Form.Group>
          <Button variant="success" type="submit" className="w-100">
            Sign In with Email
          </Button>
        </Form>

        <div className="labels text-center mt-3">
          <small>
            New user?{" "}
            <span role="button" className="auth-link" onClick={() => navigate("/signup")}>
              Sign Up
            </span>
          </small>
        </div>
      </div>
    </div>
  );
}

export default SignIn;