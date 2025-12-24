/**
 * @jest-environment jsdom
 */
import { screen, fireEvent, waitFor } from '@testing-library/dom';
import '@testing-library/jest-dom';

describe('Form Validation', () => {
  beforeEach(() => {
    // Setup DOM
    document.body.innerHTML = `
      <form id="loginForm">
        <input type="email" id="email" required />
        <input type="password" id="password" required minlength="6" />
        <button type="submit" id="submitBtn">Login</button>
        <div id="errorMessage"></div>
      </form>
    `;
  });

  test('should show error for empty email', async () => {
    const form = document.getElementById('loginForm');
    const emailInput = document.getElementById('email');
    const submitBtn = document.getElementById('submitBtn');
    const errorDiv = document.getElementById('errorMessage');

    // Mock form submission
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      if (!emailInput.value) {
        errorDiv.textContent = 'Email é obrigatório';
      }
    });

    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(errorDiv).toHaveTextContent('Email é obrigatório');
    });
  });

  test('should validate password length', () => {
    const passwordInput = document.getElementById('password');

    fireEvent.change(passwordInput, { target: { value: '12345' } });
    expect(passwordInput.validity.valid).toBe(false);

    fireEvent.change(passwordInput, { target: { value: '123456' } });
    expect(passwordInput.validity.valid).toBe(true);
  });

  test('should handle successful form submission', async () => {
    const form = document.getElementById('loginForm');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const submitBtn = document.getElementById('submitBtn');

    // Mock successful API call
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ success: true })
      })
    );

    // Fill form
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });

    // Mock form submission
    let submitted = false;
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      submitted = true;
    });

    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(submitted).toBe(true);
      expect(global.fetch).toHaveBeenCalledWith('/auth/login', expect.any(Object));
    });
  });
});