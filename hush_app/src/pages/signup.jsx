import React, { useState, useContext } from "react";
import { Button, Form } from "react-bootstrap";
import { useNavigate } from "react-router-dom";
import "bootstrap/dist/css/bootstrap.min.css";
import "../styles/Auth.css";
import "../styles/Splash.css";
import Image from "../assets/Brand_logo.png";
import { GoogleLogin } from '@react-oauth/google';
import axios from 'axios';
import { toast } from 'react-toastify';
import UserContext from "../UserContext/userContext";
import ConsentModal from "../components/ConsentModal";

function SignUp() {
  const navigate = useNavigate();
  const { setUser } = useContext(UserContext);
  const [showConsentModal, setShowConsentModal] = useState(false);
  const [authResponse, setAuthResponse] = useState(null);

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: ''
  });

  const handleInputChange = (e) => {
    const { id, value } = e.target;
    setFormData(prev => ({ ...prev, [id]: value }));
  };

  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      const res = await axios.post("http://localhost:8000/auth/google", {
        token: credentialResponse.credential
      });
      setAuthResponse(res.data);

      if (res.data.user && res.data.user.linkedin && res.data.user.github) {
        toast.info("This account already exists. Please sign in.");
        navigate('/signin');
      } else {
        setShowConsentModal(true);
      }
    } catch (err) {
      console.error("Authentication failed:", err);
      toast.error("Google authentication failed.");
    }
  };

  const handleConsentAgree = () => {
    if (authResponse && authResponse.user) {
      setUser({
        name: authResponse.user.name,
        email: authResponse.user.email,
        consentToken: authResponse.consent_token,
      });
      setShowConsentModal(false);
      navigate("/FormSignup");
    }
  };

  const handleConsentDecline = () => {
    setShowConsentModal(false);
    setAuthResponse(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post("http://localhost:8000/api/signup-email", {
        name: formData.name,
        email: formData.email,
        password: formData.password
      });

      setUser({
        name: formData.name,
        email: formData.email,
        consentToken: null, 
      });

      toast.success("Account created! Please provide a few more details.");
      navigate("/FormSignup");

    } catch (error) {
      if (error.response && error.response.status === 400) {
        toast.error("An account with this email already exists.");
      } else {
        toast.error("Failed to create account. Please try again.");
      }
      console.error("Signup failed:", error);
    }
  };

  return (
    <>
      <ConsentModal
        show={showConsentModal}
        onAgree={handleConsentAgree}
        onDecline={handleConsentDecline}
      />
      <div className="auth-container">
        <div className="auth-card">
          <img className="brand-image d-block mx-auto mb-3" src={Image} alt="Brand Logo" />
          <h3 className="auth-title">Create an Account</h3>
          
          <div className="google-btn-wrapper w-100 my-3">
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={() => console.log("Login Failed")}
              theme="filled_black" text="signup_with" shape="rectangular"
            />
          </div>
          
          <div className="divider">
            <hr className="flex-grow-1" />
            <span className="text-white fw-lighter">or continue with email</span>
            <hr className="flex-grow-1" />
          </div>

          <Form onSubmit={handleSubmit}>
            <Form.Group className="mb-3" controlId="name">
              <Form.Label className="labels">Full Name</Form.Label>
              <Form.Control type="text" placeholder="Enter your name" required onChange={handleInputChange} value={formData.name} />
            </Form.Group>
            <Form.Group className="mb-3" controlId="email">
              <Form.Label className="labels">Email address</Form.Label>
              <Form.Control type="email" placeholder="Enter email" required onChange={handleInputChange} value={formData.email} />
            </Form.Group>
            <Form.Group className="mb-4" controlId="password">
              <Form.Label className="labels">Password</Form.Label>
              <Form.Control type="password" placeholder="Create password" required onChange={handleInputChange} value={formData.password} />
            </Form.Group>
            <Button variant="success" type="submit" className="w-100">
              Create Account
            </Button>
          </Form>

          <div className="labels text-center mt-3">
            <small>
              Already have an account?{" "}
              <span role="button" className="auth-link" onClick={() => navigate("/signin")}>
                Sign In
              </span>
            </small>
          </div>
        </div>
      </div>
    </>
  );
}

export default SignUp;
