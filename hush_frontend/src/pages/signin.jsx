import React from "react";
import { Button, Form } from "react-bootstrap";
import { useNavigate } from "react-router-dom";
import "bootstrap/dist/css/bootstrap.min.css";
import "../styles/Auth.css";
import "../styles/Splash.css";
import Image from "../assets/Brand_logo.png";
import GoogleLogo from "../assets/Google_logo.png"

function SignIn() {
  const navigate = useNavigate();

  const handleSubmit = (e) => {
    e.preventDefault();
    // TODO: Add authentication logic
    navigate("/inbox");
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <img
            className="brand-image d-block mx-auto mb-3"
            src={Image}
            alt="Brand Logo"
          />
          <h3 className="auth-title">Welcome Back</h3>
          <h4 className="auth-subtitle ">Sign In to continue using our agent</h4>
        </div>
        <Button className="google-btn w-100 my-3">
          <img src={GoogleLogo} alt="Google" className="google-icon me-2" />
          Continue with Google
        </Button>
        <div className="divider">
          <hr className="flex-grow-1" />
          <span className="px-2 text-white fw-lighter">or continue with email</span>
          <hr className="flex-grow-1" />
        </div>
        <Form onSubmit={handleSubmit}>
          <Form.Group className="mb-3" controlId="formEmail">
            <Form.Label className="labels">Email address</Form.Label>
            <Form.Control type="email" placeholder="Enter email" required />
          </Form.Group>

          <Form.Group className="mb-4" controlId="formPassword">
            <Form.Label className="labels">Password</Form.Label>
            <Form.Control type="password" placeholder="Password" required />
          </Form.Group>

          <Button variant="success" type="submit" className="w-100">
            Sign In
          </Button>
        </Form>

        <div className="labels text-center mt-3 ">
          <small>
            New user?{" "}
            <span
              role="button"
              className="auth-link"
              onClick={() => navigate("/signup")}
            >
              Sign Up
            </span>
          </small>
        </div>
      </div>
    </div>
  );
}

export default SignIn;