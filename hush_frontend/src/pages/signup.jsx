import React from "react";
import { Button, Form } from "react-bootstrap";
import { useNavigate } from "react-router-dom";
import "bootstrap/dist/css/bootstrap.min.css";
import "../styles/Auth.css";
import "../styles/Splash.css";
import Image from "../assets/Brand_logo.png";
import GoogleLogo from "../assets/Google_logo.png"

function SignUp() {
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    // TODO: Add sign-up logic
    navigate("/signin");
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <img className="brand-image d-block mx-auto mb-3" src={Image} alt="Brand Logo" />
        <h3 className="auth-title">Welcome</h3>
        <h3 className="auth-subtitle">Sign Up to start using our agent</h3>
        <Form onSubmit={handleSubmit}>
          <Form.Group className="mb-3" controlId="formName">
            <Form.Label className="labels">Full Name</Form.Label>
            <Form.Control type="text" placeholder="Enter your name" required />
          </Form.Group>
          <Form.Group className="mb-3" controlId="formEmail">
            <Form.Label className="labels">Email address</Form.Label>
            <Form.Control type="email" placeholder="Enter email" required />
          </Form.Group>

          <Form.Group className="mb-4" controlId="formPassword">
            <Form.Label className="labels">Password</Form.Label>
            <Form.Control type="password" placeholder="Create password" required />
          </Form.Group>

          <Button variant="success" type="submit" className="w-100">
            Create Account
          </Button>
        </Form>
        <div className="divider">
            <hr className="flex-grow-1" />
            <span className="px-2 text-white fw-lighter">or continue with your Google account</span>
            <hr className="flex-grow-1" />
          </div>
        <Button className="google-btn w-100 my-3">
          <img src={GoogleLogo} alt="Google" className="google-icon me-2" />
          Continue with Google
        </Button>
        <div className="labels text-center mt-3">
          <small>
            Already have an account?{" "}
            <span
              role="button"
              className="auth-link"
              onClick={() => navigate("/signin")}
            >
              Sign In
            </span>
          </small>
        </div>
      </div>
    </div>
  );
}

export default SignUp;