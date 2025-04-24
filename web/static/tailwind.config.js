module.exports = {
  content: ["../templates/*.html"],
  theme: {
    extend: {
      fontFamily: {
        poppins: ['Poppins', 'sans-serif'],
      },
      colors: {
        'dark-blue': '#1F2A44',
        'sidebar-bg': '#2C3E50',
        'sidebar-menu': '#3A506B',
        'sidebar-hover': '#4A6FA5',
        'light-bg': '#f0f2f5',
        'light-gray': '#e9ecef',
        'text-dark': '#333',
        'text-light': '#E6F0FA',
        'teal': '#4BC0C0',
        'blue-hover': '#36A2EB',
        'red-error': '#DC3545',
        'red-hover': '#C82333',
        'gray-light': '#f8f9fa',
        'gray-dark': '#34495E',
        'gray-border': '#e0e0e0',
        'gray-medium': '#6c757d',
        'green-success': '#28a745',
      },
      boxShadow: {
        'light': '0 4px 15px rgba(0, 0, 0, 0.1)',
        'medium': '0 4px 20px rgba(0, 0, 0, 0.1)',
        'dark': '0 4px 20px rgba(0, 0, 0, 0.3)',
        'small': '0 2px 5px rgba(0, 0, 0, 0.05)',
        'menu': '0 2px 5px rgba(0, 0, 0, 0.2)',
        'card-hover': '0 8px 30px rgba(0, 0, 0, 0.2)',
      },
      animation: {
        'fadeIn': 'fadeIn 0.5s ease-in-out',
        'slideInDown': 'slideInDown 0.5s ease-in-out',
        'slideInUp': 'slideInUp 0.5s ease-in-out',
        'spin': 'spin 1s linear infinite',
        'pulse': 'pulse 1.5s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideInDown: {
          '0%': { transform: 'translateY(-20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideInUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        spin: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        pulse: {
          '0%': { opacity: '1' },
          '50%': { opacity: '0.5' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}