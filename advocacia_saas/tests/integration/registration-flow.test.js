/**
 * @jest-environment jsdom
 */
import { screen, fireEvent, waitFor } from '@testing-library/dom';
import '@testing-library/jest-dom';

describe('User Registration Flow', () => {
  beforeEach(() => {
    // Setup registration page DOM
    document.body.innerHTML = `
      <div id="registrationPage">
        <h1>Criar Conta</h1>
        <form id="registrationForm">
          <div class="form-group">
            <label for="name">Nome Completo</label>
            <input type="text" id="name" required />
          </div>
          <div class="form-group">
            <label for="email">Email</label>
            <input type="email" id="email" required />
          </div>
          <div class="form-group">
            <label for="oab">OAB</label>
            <input type="text" id="oab" required />
          </div>
          <div class="form-group">
            <label for="password">Senha</label>
            <input type="password" id="password" required minlength="8" />
          </div>
          <div class="form-group">
            <label for="confirmPassword">Confirmar Senha</label>
            <input type="password" id="confirmPassword" required />
          </div>
          <button type="submit" id="registerBtn">Criar Conta</button>
        </form>
        <div id="message"></div>
      </div>
    `;
  });

  test('should complete full registration flow', async () => {
    const form = document.getElementById('registrationForm');
    const nameInput = document.getElementById('name');
    const emailInput = document.getElementById('email');
    const oabInput = document.getElementById('oab');
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    const registerBtn = document.getElementById('registerBtn');
    const messageDiv = document.getElementById('message');

    // Mock API responses
    global.fetch = jest.fn()
      .mockImplementationOnce(() => // OAB validation
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ valid: true, name: 'João Silva' })
        })
      )
      .mockImplementationOnce(() => // Registration
        Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            success: true,
            user: { id: 1, email: 'joao@example.com' }
          })
        })
      );

    // Fill form with valid data
    fireEvent.change(nameInput, { target: { value: 'João Silva' } });
    fireEvent.change(emailInput, { target: { value: 'joao@example.com' } });
    fireEvent.change(oabInput, { target: { value: '123456' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });
    fireEvent.change(confirmPasswordInput, { target: { value: 'password123' } });

    // Mock form submission with validation
    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      // Validate OAB first
      const oabResponse = await fetch('/api/validate-oab', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ oab: oabInput.value })
      });

      if (oabResponse.ok) {
        // Then register user
        const registerResponse = await fetch('/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: nameInput.value,
            email: emailInput.value,
            oab: oabInput.value,
            password: passwordInput.value
          })
        });

        if (registerResponse.ok) {
          messageDiv.textContent = 'Conta criada com sucesso!';
          messageDiv.className = 'success';
        }
      }
    });

    fireEvent.click(registerBtn);

    await waitFor(() => {
      expect(messageDiv).toHaveTextContent('Conta criada com sucesso!');
      expect(messageDiv).toHaveClass('success');
    });

    // Verify API calls
    expect(global.fetch).toHaveBeenCalledTimes(2);
    expect(global.fetch).toHaveBeenNthCalledWith(1, '/api/validate-oab', expect.any(Object));
    expect(global.fetch).toHaveBeenNthCalledWith(2, '/auth/register', expect.any(Object));
  });

  test('should handle OAB validation failure', async () => {
    const oabInput = document.getElementById('oab');
    const messageDiv = document.getElementById('message');

    // Mock failed OAB validation
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: false,
        json: () => Promise.resolve({ error: 'OAB inválida ou não encontrada' })
      })
    );

    // Trigger OAB validation (assuming there's a blur handler)
    fireEvent.blur(oabInput, { target: { value: 'invalid-oab' } });

    // Simulate validation call
    const response = await fetch('/api/validate-oab', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ oab: 'invalid-oab' })
    });

    if (!response.ok) {
      const data = await response.json();
      messageDiv.textContent = data.error;
      messageDiv.className = 'error';
    }

    await waitFor(() => {
      expect(messageDiv).toHaveTextContent('OAB inválida ou não encontrada');
      expect(messageDiv).toHaveClass('error');
    });
  });
});