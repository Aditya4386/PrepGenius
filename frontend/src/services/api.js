const API_BASE = '/api/v1';

/**
 * Returns authentication headers.
 * Extracts token from localStorage.
 */
export function getAuthHeaders() {
  const token = localStorage.getItem('prepgenius_auth_token');
  const headers = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export function getStoredStudent() {
  const data = localStorage.getItem('prepgenius_student');
  if (data) {
    try {
      return JSON.parse(data);
    } catch {
      return null;
    }
  }
  return null;
}

export function saveAuthSession(token, student) {
  localStorage.setItem('prepgenius_auth_token', token);
  localStorage.setItem('prepgenius_student', JSON.stringify(student));
}

export function clearAuthSession() {
  localStorage.removeItem('prepgenius_auth_token');
  localStorage.removeItem('prepgenius_student');
}

// ----------------- Auth API -----------------

export async function apiRegister({ fullName, email, password }) {
  const response = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      full_name: fullName,
      email,
      password,
    }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    let msg = data.detail;
    if (Array.isArray(msg)) {
      msg = msg.map(err => `${err.loc?.join('.')}: ${err.msg}`).join(', ');
    }
    throw new Error(msg || `Registration failed (${response.status})`);
  }

  saveAuthSession(data.access_token, data.student);
  return data;
}

export async function apiLogin({ email, password }) {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    let msg = data.detail;
    if (Array.isArray(msg)) {
      msg = msg.map(err => `${err.loc?.join('.')}: ${err.msg}`).join(', ');
    }
    throw new Error(msg || `Login failed (${response.status})`);
  }

  saveAuthSession(data.access_token, data.student);
  return data;
}

export async function apiGetMe() {
  const response = await fetch(`${API_BASE}/auth/me`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error('Session expired or unauthorized');
  }

  return response.json();
}

// ----------------- Profile API -----------------

export async function fetchProfile() {
  const response = await fetch(`${API_BASE}/profile`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to fetch profile (${response.status})`);
  }

  return response.json();
}

export async function saveProfile(profileData) {
  const response = await fetch(`${API_BASE}/profile`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify(profileData),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    let msg = errorData.detail;
    if (Array.isArray(msg)) {
      msg = msg.map(err => `${err.loc?.join('.')}: ${err.msg}`).join(', ');
    }
    throw new Error(msg || `Failed to update profile (${response.status})`);
  }

  return response.json();
}

export async function fetchHealth() {
  const response = await fetch('/health');
  return response.json();
}
