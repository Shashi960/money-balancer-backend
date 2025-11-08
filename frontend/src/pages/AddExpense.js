import { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate, useLocation } from "react-router-dom";
import { toast } from "sonner";
import { Plus, DollarSign, Edit } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const categories = ['Food', 'Travel', 'Shopping', 'Bills', 'Entertainment', 'Healthcare', 'Education', 'Other'];

export default function AddExpense() {
  const navigate = useNavigate();
  const location = useLocation();
  const editExpense = location.state?.expense;
  
  const [formData, setFormData] = useState({
    title: '',
    amount: '',
    date: new Date().toISOString().split('T')[0],
    category: 'Food'
  });

  useEffect(() => {
    if (editExpense) {
      setFormData({
        title: editExpense.title,
        amount: editExpense.amount,
        date: editExpense.date,
        category: editExpense.category
      });
    }
  }, [editExpense]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.title || !formData.amount) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      if (editExpense) {
        // Update existing expense
        await axios.patch(`${API}/expenses/${editExpense.id}`, {
          ...formData,
          amount: parseFloat(formData.amount)
        });
        toast.success('Expense updated successfully!');
      } else {
        // Create new expense
        await axios.post(`${API}/expenses`, {
          ...formData,
          amount: parseFloat(formData.amount)
        });
        toast.success('Expense added successfully!');
      }
      navigate('/');
    } catch (error) {
      console.error('Error saving expense:', error);
      toast.error('Failed to save expense');
    }
  };

  return (
    <div className="page-container" data-testid="add-expense-page">
      <div className="page-header">
        <h1 className="page-title">{editExpense ? 'Edit Expense' : 'Add Expense'}</h1>
        <p className="page-subtitle">Track your daily spending</p>
      </div>

      <div className="card" style={{ maxWidth: '600px', margin: '0 auto' }}>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="title">Title / Reason *</label>
            <input
              id="title"
              type="text"
              className="form-input"
              placeholder="e.g., Grocery shopping"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              data-testid="expense-title-input"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="amount">Amount (₹) *</label>
            <div style={{ position: 'relative' }}>
              <span style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: '#718096', fontSize: '1.25rem' }}>₹</span>
              <input
                id="amount"
                type="number"
                step="0.01"
                className="form-input"
                placeholder="0.00"
                style={{ paddingLeft: '3rem' }}
                value={formData.amount}
                onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                data-testid="expense-amount-input"
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="date">Date *</label>
            <input
              id="date"
              type="date"
              className="form-input"
              value={formData.date}
              onChange={(e) => setFormData({ ...formData, date: e.target.value })}
              data-testid="expense-date-input"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="category">Category *</label>
            <select
              id="category"
              className="form-select"
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              data-testid="expense-category-select"
            >
              {categories.map((cat) => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', gap: '1rem', marginTop: '2rem' }}>
            <button type="submit" className="btn btn-primary" data-testid="submit-expense-btn" style={{ flex: 1 }}>
              {editExpense ? <><Edit size={20} /> Update Expense</> : <><Plus size={20} /> Add Expense</>}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => navigate('/')}
              data-testid="cancel-expense-btn"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}