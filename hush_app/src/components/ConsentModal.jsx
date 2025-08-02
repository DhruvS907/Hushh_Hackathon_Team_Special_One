// src/components/ConsentModal.jsx
import React from 'react';
import { Modal, Button } from 'react-bootstrap';
import '../styles/ConsentModal.css';

function ConsentModal({ show, onAgree, onDecline }) {
  return (
    <Modal show={show} onHide={onDecline} centered backdrop="static" keyboard={false}>
      <Modal.Header>
        <Modal.Title>Permission Request</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <h5>Allow Access to Your Emails</h5>
        <p>
          To provide smart summaries and generate intelligent replies, our agent needs temporary, read-only access to your emails.
        </p>
        <ul className="permissions-list">
          <li> We will only analyze unread emails from the last 24 hours.</li>
          <li> Your email content is processed securely and is never stored.</li>
          <li> You can revoke this permission at any time from your settings.</li>
        </ul>
        <p className="consent-question">
          Do you agree to grant these permissions?
        </p>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="outline-secondary" onClick={onDecline}>
          Decline
        </Button>
        <Button variant="primary" onClick={onAgree}>
          Agree & Continue
        </Button>
      </Modal.Footer>
    </Modal>
  );
}

export default ConsentModal;