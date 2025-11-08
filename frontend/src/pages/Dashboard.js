import { useEffect, useState } from "react";
import axios from "axios";
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { Wallet, TrendingUp, TrendingDown, AlertCircle, DollarSign, HandCoins } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const COLORS = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b'];

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [summaryRes, expensesRes] = await Promise.all([
        axios.get(`${API}/summary`),
        axios.get(`${API}/expenses?filter=month`)
      ]);
      setSummary(summaryRes.data);
      setExpenses(expensesRes.data);
    } catch (error) {
      console.error("Error fetching data:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="page-header">
          <h1 className="page-title">Loading...</h1>
        </div>
      </div>
    );
  }

  if (!summary) return null;

  // Prepare category data for pie chart
  const categoryData = expenses.reduce((acc, expense) => {
    const existing = acc.find(item => item.name === expense.category);
    if (existing) {
      existing.value += expense.amount;
    } else {
      acc.push({ name: expense.category, value: expense.amount });
    }
    return acc;
  }, []);

  // Prepare weekly data for bar chart (last 7 days)
  const last7Days = [];
  const today = new Date();
  for (let i = 6; i >= 0; i--) {
    const date = new Date(today);
    date.setDate(date.getDate() - i);
    const dateStr = date.toISOString().split('T')[0];
    const dayExpenses = expenses.filter(e => e.date === dateStr);
    const total = dayExpenses.reduce((sum, e) => sum + e.amount, 0);
    last7Days.push({
      date: dateStr,
      day: date.toLocaleDateString('en-US', { weekday: 'short' }),
      amount: total
    });
  }

  return (
    <div className="page-container" data-testid="dashboard">
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">Your financial overview at a glance</p>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card" data-testid="stat-today">
          <div className="stat-header">
            <div className="stat-icon">
              <DollarSign size={24} />
            </div>
          </div>
          <div className="card-title">Today's Spending</div>
          <div className="card-value">₹{summary.total_today.toFixed(2)}</div>
        </div>

        <div className="stat-card" data-testid="stat-week">
          <div className="stat-header">
            <div className="stat-icon">
              <TrendingUp size={24} />
            </div>
          </div>
          <div className="card-title">This Week</div>
          <div className="card-value">₹{summary.total_week.toFixed(2)}</div>
          {summary.weekly_limit > 0 && (
            <div className="card-subtitle">
              ₹{summary.remaining_week.toFixed(2)} remaining
              {summary.weekly_warning === 'yellow' && (
                <span className="warning-badge warning-yellow" style={{ marginLeft: '0.5rem' }}>
                  <AlertCircle size={14} /> 80% Used
                </span>
              )}
              {summary.weekly_warning === 'red' && (
                <span className="warning-badge warning-red" style={{ marginLeft: '0.5rem' }}>
                  <AlertCircle size={14} /> Limit Exceeded!
                </span>
              )}
            </div>
          )}
        </div>

        <div className="stat-card" data-testid="stat-month">
          <div className="stat-header">
            <div className="stat-icon">
              <Wallet size={24} />
            </div>
          </div>
          <div className="card-title">This Month</div>
          <div className="card-value">₹{summary.total_month.toFixed(2)}</div>
          {summary.monthly_limit > 0 && (
            <div className="card-subtitle">
              ₹{summary.remaining_month.toFixed(2)} remaining
              {summary.monthly_warning === 'yellow' && (
                <span className="warning-badge warning-yellow" style={{ marginLeft: '0.5rem' }}>
                  <AlertCircle size={14} /> 80% Used
                </span>
              )}
              {summary.monthly_warning === 'red' && (
                <span className="warning-badge warning-red" style={{ marginLeft: '0.5rem' }}>
                  <AlertCircle size={14} /> Limit Exceeded!
                </span>
              )}
            </div>
          )}
        </div>

        <div className="stat-card" data-testid="stat-debts">
          <div className="stat-header">
            <div className="stat-icon">
              <HandCoins size={24} />
            </div>
          </div>
          <div className="card-title">Money Tracking</div>
          <div className="card-value" style={{ fontSize: '1.5rem' }}>
            <div style={{ marginBottom: '0.5rem' }}>
              <TrendingDown size={20} style={{ color: '#10b981', display: 'inline', marginRight: '0.5rem' }} />
              ₹{summary.money_gave.toFixed(2)} Lent
            </div>
            <div>
              <TrendingUp size={20} style={{ color: '#ef4444', display: 'inline', marginRight: '0.5rem' }} />
              ₹{summary.money_owe.toFixed(2)} Owe
            </div>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginTop: '2rem' }}>
        {/* Bar Chart - Weekly Spending */}
        <div className="card" data-testid="weekly-chart">
          <h3 className="card-title">Last 7 Days Spending</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={last7Days}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="day" stroke="#718096" />
              <YAxis stroke="#718096" />
              <Tooltip />
              <Bar dataKey="amount" fill="#667eea" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Pie Chart - Category Breakdown */}
        <div className="card" data-testid="category-chart">
          <h3 className="card-title">Spending by Category</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={categoryData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {categoryData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}