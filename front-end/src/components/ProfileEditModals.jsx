import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { Save, University, UserPen, X } from 'lucide-react'

export function EditPersonalModal({ open, onClose, profile, onSave }) {
  const [form, setForm] = useState(profile)

  useEffect(() => {
    if (open) setForm(profile)
  }, [open, profile])

  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [open, onClose])

  if (!open) return null

  const set = (key) => (e) => setForm((prev) => ({ ...prev, [key]: e.target.value }))

  const submit = (e) => {
    e.preventDefault()
    onSave({
      ...form,
      fullName: `${form.firstName} ${form.lastName}`.trim(),
    })
    onClose()
  }

  return createPortal(
    <div className="modal-overlay" onClick={onClose} role="presentation">
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
          <button type="button" className="modal-close" aria-label="Close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={submit}>
          <div className="modal-body profile-form-body">
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
            <button type="button" className="btn btn-ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              <Save size={16} />
              Save Changes
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body,
  )
}

export function EditBankModal({ open, onClose, profile, onSave }) {
  const [form, setForm] = useState({
    bankName: profile.bankName,
    bankAccountNumber: profile.bankAccountNumber,
    bankAccountName: profile.bankAccountName,
  })

  useEffect(() => {
    if (open) {
      setForm({
        bankName: profile.bankName,
        bankAccountNumber: profile.bankAccountNumber,
        bankAccountName: profile.bankAccountName,
      })
    }
  }, [open, profile])

  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [open, onClose])

  if (!open) return null

  const set = (key) => (e) => setForm((prev) => ({ ...prev, [key]: e.target.value }))

  const submit = (e) => {
    e.preventDefault()
    onSave(form)
    onClose()
  }

  return createPortal(
    <div className="modal-overlay" onClick={onClose} role="presentation">
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
          <button type="button" className="modal-close" aria-label="Close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={submit}>
          <div className="modal-body profile-form-body">
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
            <button type="button" className="btn btn-ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              <Save size={16} />
              Save Changes
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body,
  )
}
