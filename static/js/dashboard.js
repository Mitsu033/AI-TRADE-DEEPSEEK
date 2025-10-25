/**
 * 共通JavaScriptファイル
 * ボット制御、ステータス更新などの共通機能
 */

// テーマ管理
function initTheme() {
    // ローカルストレージからテーマを読み込む
    const savedTheme = localStorage.getItem('theme') || 'dark';
    if (savedTheme === 'light') {
        document.body.classList.add('light-mode');
        updateThemeIcon('light');
    } else {
        updateThemeIcon('dark');
    }
}

function toggleTheme() {
    const body = document.body;
    const isLight = body.classList.contains('light-mode');
    
    if (isLight) {
        // ダークモードに切り替え
        body.classList.remove('light-mode');
        localStorage.setItem('theme', 'dark');
        updateThemeIcon('dark');
        showNotification('ダークモードに切り替えました', 'info');
    } else {
        // ライトモードに切り替え
        body.classList.add('light-mode');
        localStorage.setItem('theme', 'light');
        updateThemeIcon('light');
        showNotification('ライトモードに切り替えました', 'info');
    }
    
    // チャートを再描画（テーマに合わせて）
    setTimeout(() => {
        window.location.reload();
    }, 500);
}

function updateThemeIcon(theme) {
    const themeIcon = document.querySelector('.theme-icon');
    if (themeIcon) {
        themeIcon.textContent = theme === 'light' ? 'Dark' : 'Light';
    }
}

// ボットステータスを更新
function updateBotStatus(status) {
    const statusElement = document.getElementById('bot-status');
    const statusText = statusElement.querySelector('.status-text');
    
    if (status === 'running') {
        statusElement.className = 'bot-status running';
        statusText.textContent = '稼働中';
    } else {
        statusElement.className = 'bot-status stopped';
        statusText.textContent = '停止中';
    }
}

// ボットを開始
async function startBot() {
    try {
        const response = await fetch('/api/bot/start', {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.error) {
            alert(`エラー: ${data.error}`);
            return;
        }
        
        updateBotStatus(data.status);
        showNotification('ボットを開始しました', 'success');
    } catch (error) {
        console.error('Error starting bot:', error);
        showNotification('ボット開始エラー', 'error');
    }
}

// ボットを停止
async function stopBot() {
    try {
        const response = await fetch('/api/bot/stop', {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.error) {
            alert(`エラー: ${data.error}`);
            return;
        }
        
        updateBotStatus(data.status);
        showNotification('ボットを停止しました', 'info');
    } catch (error) {
        console.error('Error stopping bot:', error);
        showNotification('ボット停止エラー', 'error');
    }
}

// 通知を表示
function showNotification(message, type = 'info') {
    // 既存の通知を削除
    const existing = document.querySelector('.notification');
    if (existing) {
        existing.remove();
    }
    
    // 通知要素を作成
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // スタイルを追加
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        background: ${type === 'success' ? '#00ff88' : type === 'error' ? '#ff4444' : '#00aaff'};
        color: ${type === 'success' || type === 'error' ? '#000' : '#fff'};
        border-radius: 8px;
        font-weight: bold;
        z-index: 10000;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    // 3秒後に削除
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// アニメーションを追加
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// ボタンイベントリスナー
document.addEventListener('DOMContentLoaded', () => {
    // テーマ初期化
    initTheme();
    
    // テーマトグルボタン
    const themeToggleBtn = document.getElementById('theme-toggle');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', toggleTheme);
    }
    
    // ボット制御ボタン
    const startBtn = document.getElementById('start-bot-btn');
    const stopBtn = document.getElementById('stop-bot-btn');
    
    if (startBtn) {
        startBtn.addEventListener('click', startBot);
    }
    
    if (stopBtn) {
        stopBtn.addEventListener('click', stopBot);
    }
    
    // 初期ステータス取得
    fetchInitialStatus();
});

// 初期ステータスを取得
async function fetchInitialStatus() {
    try {
        const response = await fetch('/api/dashboard');
        const data = await response.json();
        
        if (!data.error) {
            updateBotStatus(data.status);
        }
    } catch (error) {
        console.error('Error fetching initial status:', error);
    }
}

// 数値フォーマット関数
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

function formatPercent(value) {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

// 時刻フォーマット関数
function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function formatTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleTimeString('ja-JP', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// エクスポート
window.updateBotStatus = updateBotStatus;
window.startBot = startBot;
window.stopBot = stopBot;
window.showNotification = showNotification;
window.formatCurrency = formatCurrency;
window.formatPercent = formatPercent;
window.formatDateTime = formatDateTime;
window.formatTime = formatTime;

