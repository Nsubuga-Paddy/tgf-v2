import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Save, University, UserPen, X } from 'lucide-react'

function normalizeWhatsapp(value) {
  return String(value || '').trim().replace(/[\s-]/g, '')
}

function isValidWhatsapp(value) {
  return /^\+[1-9]\d{7,14}$/.test(normalizeWhatsapp(value))
}

function snapshotPersonal(profile) {
  return {
    firstName: profile?.firstName || '',
    lastName: profile?.lastName || '',
    email: profile?.email || '',
    whatsapp: profile?.whatsapp || '',
    nationalId: profile?.nationalId || '',
    birthdate: profile?.birthdate || '',
    address: profile?.address || '',
    bio: profile?.bio || '',
  }
}

function snapshotBank(profile) {
  return {
    bankName: profile?.bankName || '',
    bankAccountNumber: profile?.bankAccountNumber || '',
    bankAccountName: profile?.bankAccountName || '',
  }
}

export function EditPersonalModal({ open, onClose, profile, onSave }) {
  const [form, setForm] = useState(() => snapshotPersonal(profile))
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const profileRef = useRef(profile)
  profileRef.current = profile

  useEffect(() => {
    if (!open) return
    setForm(snapshotPersonal(profileRef.current))
    setError('')
    setSubmitting(false)
  }, [open])

  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape' && !submitting) onClose()
    }
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [open, onClose, submitting])

  if (!open) return null

  const set = (key) => (e) => {
    const value = e.target.value
    setForm((prev) => ({ ...prev, [key]: value }))
    if (error) setError('')
  }

  const submit = async (e) => {
    e.preventDefault()
    if (submitting) return
    const whatsapp = normalizeWhatsapp(form.whatsapp)
    if (!isValidWhatsapp(whatsapp)) {
      setError('Enter a WhatsApp number beginning with a country code (e.g., +2567xxxxxxxx).')
      return
    }
    const birthdate = (form.birthdate || '').trim()
    if (birthdate && !/^\d{4}-\d{2}-\d{2}$/.test(birthdate)) {
      setError('Date of birth must be YYYY-MM-DD.')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      await onSave({
        ...form,
        firstName: (form.firstName || '').trim(),
        lastName: (form.lastName || '').trim(),
        email: (form.email || '').trim(),
        whatsapp,
        nationalId: (form.nationalId || '').trim(),
        birthdate,
        address: (form.address || '').trim(),
        bio: (form.bio || '').trim(),
        fullName: `${(form.firstName || '').trim()} ${(form.lastName || '').trim()}`.trim(),
      })
      onClose()
    } catch (err) {
      setError(err.message || 'Could not save personal information.')
    } finally {
      setSubmitting(false)
    }
  }

  return createPortal(
    <div
      className="modal-overlay"
      onClick={submitting ? undefined : onClose}
      role="presentation"
    >
      <div
        className="modal modal-wide"
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-personal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <div className="modal-head-icon">
            <UserPen size={20} />
          </div>
          <div className="modal-head-text">
            <b id="edit-personal-title">Edit Personal Information</b>
            <span>Update your contact and identity details</span>
          </div>
          <button
            type="button"
            className="modal-close"
            aria-label="Close"
            onClick={onClose}
            disabled={submitting}
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={submit}>
          <div className="modal-body profile-form-body">
            {error ? (
              <p className="profile-form-error" role="alert">
                {error}
              </p>
            ) : null}
            <div className="profile-form-grid">
              <label className="profile-field">
                <span>First Name</span>
                <input required value={form.firstName} onChange={set('firstName')} />
              </label>
              <label className="profile-field">
                <span>Last Name</span>
                <input required value={form.lastName} onChange={set('lastName')} />
              </label>
              <label className="profile-field">
                <span>Email</span>
                <input required type="email" value={form.email} onChange={set('email')} />
              </label>
              <label className="profile-field">
                <span>
                  WhatsApp Number <em>*</em>
                </span>
                <input
                  required
                  type="tel"
                  placeholder="+2567XXXXXXXX"
                  value={form.whatsapp}
                  onChange={set('whatsapp')}
                />
              </label>
              <label className="profile-field">
                <span>National ID</span>
                <input value={form.nationalId} onChange={set('nationalId')} />
              </label>
              <label className="profile-field">
                <span>Date of Birth</span>
                <input
                  type="text"
                  placeholder="YYYY-MM-DD"
                  value={form.birthdate}
                  onChange={set('birthdate')}
                />
              </label>
              <label className="profile-field full">
                <span>Address</span>
                <textarea rows={2} value={form.address} onChange={set('address')} />
              </label>
              <label className="profile-field full">
                <span>Bio</span>
                <textarea rows={2} value={form.bio} onChange={set('bio')} />
              </label>
            </div>
          </div>
          <div className="modal-foot">
            <button type="button" className="btn btn-ghost" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              <Save size={16} />
              {submitting ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body,
  )
}

export function EditBankModal({ open, onClose, profile, onSave }) {
  const [form, setForm] = useState(() => snapshotBank(profile))
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const profileRef = useRef(profile)
  profileRef.current = profile

  useEffect(() => {
    if (!open) return
    setForm(snapshotBank(profileRef.current))
    setError('')
    setSubmitting(false)
  }, [open])

  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape' && !submitting) onClose()
    }
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [open, onClose, submitting])

  if (!open) return null

  const set = (key) => (e) => {
    const value = e.target.value
    setForm((prev) => ({ ...prev, [key]: value }))
    if (error) setError('')
  }

  const submit = async (e) => {
    e.preventDefault()
    if (submitting) return
    setSubmitting(true)
    setError('')
    try {
      await onSave({
        bankName: (form.bankName || '').trim(),
        bankAccountNumber: (form.bankAccountNumber || '').trim(),
        bankAccountName: (form.bankAccountName || '').trim(),
      })
      onClose()
    } catch (err) {
      setError(err.message || 'Could not save bank details.')
    } finally {
      setSubmitting(false)
    }
  }

  return createPortal(
    <div
      className="modal-overlay"
      onClick={submitting ? undefined : onClose}
      role="presentation"
    >
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-bank-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-head">
          <div className="modal-head-icon">
            <University size={20} />
          </div>
          <div className="modal-head-text">
            <b id="edit-bank-title">Edit Bank Account Details</b>
            <span>Used for withdrawals and dividend payouts</span>
          </div>
          <button
            type="button"
            className="modal-close"
            aria-label="Close"
            onClick={onClose}
            disabled={submitting}
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={submit}>
          <div className="modal-body profile-form-body">
            {error ? (
              <p className="profile-form-error" role="alert">
                {error}
              </p>
            ) : null}
            <div className="profile-form-grid">
              <label className="profile-field full">
                <span>Bank Name</span>
                <input
                  placeholder="e.g., Centenary Bank, Stanbic Bank"
                  value={form.bankName}
                  onChange={set('bankName')}
                />
              </label>
              <label className="profile-field full">
                <span>Account Number</span>
                <input
                  placeholder="Your bank account number"
                  value={form.bankAccountNumber}
                  onChange={set('bankAccountNumber')}
                />
              </label>
              <label className="profile-field full">
                <span>Account Name</span>
                <input
                  placeholder="Name as it appears on the account"
                  value={form.bankAccountName}
                  onChange={set('bankAccountName')}
                />
              </label>
            </div>
          </div>
          <div className="modal-foot">
            <button type="button" className="btn btn-ghost" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              <Save size={16} />
              {submitting ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body,
  )
}
