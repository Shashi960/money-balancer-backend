import { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Plus, Check, X, Trash2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Debts() {
  const [debts, setDebts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    amount: '',
    reason: '',
    date: new Date().toISOString().split('T')[0],
    debt_type: 'gave'
  });

  useEffect(() => {
    fetchDebts();
  }, []);

  const fetchDebts = async () => {
    try {
      const response = await axios.get(`${API}/debts`);
      setDebts(response.data);
    } catch (error) {
      console.error('Error fetching debts:', error);
      toast.error('Failed to fetch debts');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.name || !formData.amount || !formData.reason) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      await axios.post(`${API}/debts`, {
        ...formData,
        amount: parseFloat(formData.amount)
      });
      toast.success('Debt entry added successfully!');
      setOpenDialog(false);
      setFormData({
        name: '',
        amount: '',
        reason: '',
        date: new Date().toISOString().split('T')[0],
        debt_type: 'gave'
      });
      fetchDebts();
    } catch (error) {
      console.error('Error adding debt:', error);
      toast.error('Failed to add debt entry');
    }
  };

  const updateStatus = async (debtId, status) => {
    try {
      await axios.patch(`${API}/debts/${debtId}`, { status });
      toast.success(`Marked as ${status}`);
      fetchDebts();
    } catch (error) {
      console.error('Error updating debt:', error);
      toast.error('Failed to update debt');
    }
  };

  const deleteDebt = async (debtId) => {
    if (!window.confirm('Are you sure you want to delete this debt entry?')) {
      return;
    }
    
    try {
      await axios.delete(`${API}/debts/${debtId}`);
      toast.success('Debt entry deleted');
      fetchDebts();
    } catch (error) {
      console.error('Error deleting debt:', error);
      toast.error('Failed to delete debt');
    }
  };

  const moneyGave = debts.filter(d => d.debt_type === 'gave');
  const moneyOwe = debts.filter(d => d.debt_type === 'owe');

  if (loading) {
    return <div className="page-container"><h1 className="page-title">Loading...</h1></div>;
  }

  return (
    <div className="page-container" data-testid="debts-page">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 className="page-title">Debts Tracker</h1>
          <p className="page-subtitle">Manage money you've lent or borrowed</p>
        </div>
        <Dialog open={openDialog} onOpenChange={setOpenDialog}>
          <DialogTrigger asChild>
            <Button className="btn btn-primary" data-testid="add-debt-btn">
              <Plus size={20} />
              Add Entry
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Debt Entry</DialogTitle>
              <DialogDescription>Add a new money lent or borrowed entry</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label className="form-label">Type *</label>
                <select
                  className="form-select"
                  value={formData.debt_type}
                  onChange={(e) => setFormData({ ...formData, debt_type: e.target.value })}
                  data-testid="debt-type-select"
                >
                  <option value="gave">Money I Gave (They owe me)</option>
                  <option value="owe">Money I Owe (I need to pay)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Name *</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Person's name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  data-testid="debt-name-input"
                />
              </div>

              <div className="form-group">
                <label className="form-label">Amount (₹) *</label>
                <input
                  type="number"
                  step="0.01"
                  className="form-input"
                  placeholder="0.00"
                  value={formData.amount}
                  onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                  data-testid="debt-amount-input"
                />
              </div>

              <div className="form-group">
                <label className="form-label">Reason *</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="What was it for?"
                  value={formData.reason}
                  onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                  data-testid="debt-reason-input"
                />
              </div>

              <div className="form-group">
                <label className="form-label">Date *</label>
                <input
                  type="date"
                  className="form-input"
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  data-testid="debt-date-input"
                />
              </div>

              <Button type="submit" className="btn btn-primary" style={{ width: '100%' }} data-testid="submit-debt-btn">
                Add Entry
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Money I Gave Section */}
      <div style={{ marginTop: '2rem' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '1rem', color: '#2d3748' }} data-testid="money-gave-section">
          💸 Money I Gave (People owe me)
        </h2>
        <div className="card">
          {moneyGave.length === 0 ? (
            <p style={{ color: '#718096', textAlign: 'center', padding: '2rem' }}>No entries yet</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Amount</th>
                  <th>Reason</th>
                  <th>Date</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {moneyGave.map((debt) => (
                  <tr key={debt.id} data-testid={`debt-gave-${debt.id}`}>
                    <td>{debt.name}</td>
                    <td style={{ fontWeight: 600, color: '#10b981' }}>₹{debt.amount.toFixed(2)}</td>
                    <td>{debt.reason}</td>
                    <td>{new Date(debt.date).toLocaleDateString()}</td>
                    <td>
                      <span style={{
                        padding: '0.25rem 0.75rem',
                        borderRadius: '12px',
                        fontSize: '0.875rem',
                        fontWeight: 600,
                        background: debt.status === 'paid' ? '#d1fae5' : '#fef3c7',
                        color: debt.status === 'paid' ? '#065f46' : '#92400e'
                      }}>
                        {debt.status}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        {debt.status === 'pending' && (
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '0.5rem' }}
                            onClick={() => updateStatus(debt.id, 'paid')}
                            data-testid={`mark-paid-${debt.id}`}
                          >
                            <Check size={16} />
                          </button>
                        )}
                        <button
                          className="btn btn-secondary"
                          style={{ padding: '0.5rem', color: '#ef4444' }}
                          onClick={() => deleteDebt(debt.id)}
                          data-testid={`delete-debt-${debt.id}`}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Money I Owe Section */}
      <div style={{ marginTop: '2rem' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '1rem', color: '#2d3748' }} data-testid="money-owe-section">
          🤝 Money I Owe (I need to pay)
        </h2>
        <div className="card">
          {moneyOwe.length === 0 ? (
            <p style={{ color: '#718096', textAlign: 'center', padding: '2rem' }}>No entries yet</p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Amount</th>
                  <th>Reason</th>
                  <th>Date</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {moneyOwe.map((debt) => (
                  <tr key={debt.id} data-testid={`debt-owe-${debt.id}`}>
                    <td>{debt.name}</td>
                    <td style={{ fontWeight: 600, color: '#ef4444' }}>₹{debt.amount.toFixed(2)}</td>
                    <td>{debt.reason}</td>
                    <td>{new Date(debt.date).toLocaleDateString()}</td>
                    <td>
                      <span style={{
                        padding: '0.25rem 0.75rem',
                        borderRadius: '12px',
                        fontSize: '0.875rem',
                        fontWeight: 600,
                        background: debt.status === 'paid' ? '#d1fae5' : '#fef3c7',
                        color: debt.status === 'paid' ? '#065f46' : '#92400e'
                      }}>
                        {debt.status}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        {debt.status === 'pending' && (
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '0.5rem' }}
                            onClick={() => updateStatus(debt.id, 'paid')}
                            data-testid={`mark-paid-${debt.id}`}
                          >
                            <Check size={16} />
                          </button>
                        )}
                        <button
                          className="btn btn-secondary"
                          style={{ padding: '0.5rem', color: '#ef4444' }}
                          onClick={() => deleteDebt(debt.id)}
                          data-testid={`delete-debt-${debt.id}`}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}