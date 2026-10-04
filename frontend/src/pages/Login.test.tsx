import { describe, expect, it } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Login from './Login'
import Navbar from '../components/Navbar'
import { LANG_STORAGE_KEY } from '../i18n'

function renderLogin() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <Navbar isLoggedIn={false} onLogout={() => {}} />
        <Login onLogin={() => {}} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Login i18n', () => {
  it('renders Greek by default', () => {
    renderLogin()
    expect(screen.getByRole('button', { name: 'Σύνδεση' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Σύνδεση στο Meraki' })).toBeInTheDocument()
    expect(document.documentElement.lang).toBe('el')
    expect(document.title).toContain('καθαρό εισόδημα')
  })

  it('switches to English, persists the choice and updates <html lang>', async () => {
    const user = userEvent.setup()
    renderLogin()
    // Navbar + Login each render a switcher.
    expect(screen.getAllByRole('button', { name: 'EN' })).toHaveLength(2)
    await user.click(screen.getAllByRole('button', { name: 'EN' })[0])

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Log in to Meraki' })).toBeInTheDocument())
    expect(screen.getByRole('button', { name: 'Log in' })).toBeInTheDocument()
    expect(localStorage.getItem(LANG_STORAGE_KEY)).toBe('en')
    expect(document.documentElement.lang).toBe('en')
    expect(document.title).toBe('Meraki — Your true take-home')

    await user.click(screen.getAllByRole('button', { name: 'EL' })[0])
    await waitFor(() => expect(screen.getByRole('button', { name: 'Σύνδεση' })).toBeInTheDocument())
    expect(localStorage.getItem(LANG_STORAGE_KEY)).toBe('el')
    expect(document.documentElement.lang).toBe('el')
  })
})
