import { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Save, TrendingUp } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function Settings() {
  const [formData, setFormData] = useState({
    weekly_limit: '',
    monthly_limit: ''
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLimit();
  }, []);

  const fetchLimit = async () => {
    try {
      const response = await axios.get(`${API}/limit`);
      setFormData({
        weekly_limit: response.data.weekly_limit || '',
        monthly_limit: response.data.monthly_limit || ''
      });
    } catch (error) {
      console.error('Error fetching limit:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      await axios.post(`${API}/limit`, {
        weekly_limit: parseFloat(formData.weekly_limit) || 0,
        monthly_limit: parseFloat(formData.monthly_limit) || 0
      });
      toast.success('Spending limits updated successfully!');
    } catch (error) {
      console.error('Error updating limit:', error);
      toast.error('Failed to update limits');
    }
  };

  if (loading) {
    return <div className="page-container"><h1 className="page-title">Loading...</h1></div>;
  }

  return (
    <div className="page-container" data-testid="settings-page">
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-subtitle">Set your spending limits and preferences</p>
      </div>

      <div className="card" style={{ maxWidth: '600px', margin: '0 auto' }}>
        <h3 className="card-title" style={{ marginBottom: '1.5rem', fontSize: '1rem' }}>
          <TrendingUp size={20} style={{ display: 'inline', marginRight: '0.5rem' }} />
          Spending Limits
        </h3>
        
        <div style={{ background: '#eff6ff', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem', border: '1px solid #bfdbfe' }}>
          <p style={{ fontSize: '0.875rem', color: '#1e40af', lineHeight: '1.5' }}>
            Set your weekly and monthly spending limits. You'll receive a <strong>yellow warning</strong> at 80% and a <strong>red alert</strong> at 100%.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="weekly_limit">Weekly Limit</label>
            <input
              id="weekly_limit"
              type="number"
              step="0.01"
              className="form-input"
              placeholder="Enter weekly limit (e.g., 500)"
              value={formData.weekly_limit}
              onChange={(e) => setFormData({ ...formData, weekly_limit: e.target.value })}
              data-testid="weekly-limit-input"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="monthly_limit">Monthly Limit</label>
            <input
              id="monthly_limit"
              type="number"
              step="0.01"
              className="form-input"
              placeholder="Enter monthly limit (e.g., 2000)"
              value={formData.monthly_limit}
              onChange={(e) => setFormData({ ...formData, monthly_limit: e.target.value })}
              data-testid="monthly-limit-input"
            />
          </div>

          <button type="submit" className="btn btn-primary" style={{ width: '100%' }} data-testid="save-limits-btn">
            <Save size={20} />
            Save Settings
          </button>
        </form>
      </div>
    </div>
  );
}