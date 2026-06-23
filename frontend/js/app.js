// ==================== 配置 ====================
// 本地开发用 localhost，生产环境用相对路径（前后端同域名）
const API_BASE = (location.hostname === 'localhost' || location.hostname === '127.0.0.1')
    ? "http://localhost:8000"
    : "";

// ==================== 状态管理 ====================
let currentIngredients = [];
let currentRecipes = [];
let shoppingList = [];
let currentRecipeDetail = null;

// ==================== 工具函数 ====================
function showToast(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.style.opacity = '1';
    setTimeout(() => { toast.style.opacity = '0'; }, 2500);
}

function showSection(id) {
    const el = document.getElementById(id);
    if (el) {
        el.classList.remove('hidden');
        el.classList.add('animate-fade-in');
    }
}

function hideSection(id) {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
}

function scrollToSection(id) {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth' });
}

function closeModal(id) {
    document.getElementById(id).classList.add('hidden');
}

// ==================== 图片上传与识别 ====================
async function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    // 重置 input，允许再次上传（包括同一文件）
    event.target.value = '';

    // 预览
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('preview-image').src = e.target.result;
        document.getElementById('preview-image').classList.remove('hidden');
        document.getElementById('upload-placeholder').classList.add('hidden');
        document.getElementById('upload-loading').classList.remove('hidden');
    };
    reader.readAsDataURL(file);

    // 上传识别
    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch(`${API_BASE}/api/ingredients/recognize`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        document.getElementById('upload-loading').classList.add('hidden');

        if (!data.success) {
            showToast(data.error || '识别失败');
            return;
        }

        currentIngredients = data.data || [];
        renderIngredients();
        showSection('ingredients-section');
        showToast(`识别到 ${data.count} 种食材`);

        // 自动获取推荐
        setTimeout(() => getRecommendations(), 500);

    } catch (err) {
        document.getElementById('upload-loading').classList.add('hidden');
        showToast('网络错误，请检查后端是否运行');
        console.error(err);
    }
}

// ==================== 食材列表渲染 ====================
function renderIngredients() {
    const container = document.getElementById('ingredients-list');
    container.innerHTML = '';

    currentIngredients.forEach((item, index) => {
        const el = document.createElement('div');
        el.className = 'ingredient-tag ' + (item.confidence || 'medium');
        el.innerHTML = `
            <span>${item.name}</span>
            <span class="text-xs opacity-70">${item.quantity || ''}</span>
            <button onclick="removeIngredient(${index})" class="ml-1 text-xs hover:text-red-500">×</button>
        `;
        container.appendChild(el);
    });
}

function removeIngredient(index) {
    currentIngredients.splice(index, 1);
    renderIngredients();
}

function saveInventory() {
    showToast('库存已保存');
}

function clearInventory() {
    currentIngredients = [];
    renderIngredients();
    hideSection('ingredients-section');
    hideSection('recipes-section');
    document.getElementById('preview-image').classList.add('hidden');
    document.getElementById('upload-placeholder').classList.remove('hidden');
    showToast('已清空');
}

// ==================== 补充食材 ====================
function showSupplementModal() {
    document.getElementById('supplement-modal').classList.remove('hidden');
}

function addSupplements() {
    const input = document.getElementById('supplement-input').value.trim();
    if (!input) {
        closeModal('supplement-modal');
        return;
    }

    const lines = input.split('\n');
    const supplements = [];
    lines.forEach(line => {
        line = line.trim();
        if (!line) return;
        // 简单解析：前面是名称，后面是数量
        const parts = line.split(/\s+/);
        if (parts.length >= 2) {
            supplements.push({
                name: parts.slice(0, -1).join(''),
                quantity: parts[parts.length - 1]
            });
        } else {
            supplements.push({ name: line, quantity: '若干' });
        }
    });

    supplements.forEach(s => {
        currentIngredients.push({
            name: s.name,
            quantity: s.quantity,
            confidence: 'user'
        });
    });

    renderIngredients();
    document.getElementById('supplement-input').value = '';
    closeModal('supplement-modal');
    showToast(`已添加 ${supplements.length} 种食材`);
    showSection('ingredients-section');
}

function startVoiceInput() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        showToast('您的浏览器不支持语音输入');
        return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = 'zh-CN';
    recognition.continuous = false;
    recognition.interimResults = false;

    const textarea = document.getElementById('supplement-input');
    const voiceBtn = event.target;
    voiceBtn.textContent = '🎤 聆听中...';
    voiceBtn.classList.add('voice-recording');

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        textarea.value += (textarea.value ? '\n' : '') + transcript;
        voiceBtn.textContent = '🎤 语音';
        voiceBtn.classList.remove('voice-recording');
        showToast('语音识别完成');
    };

    recognition.onerror = () => {
        voiceBtn.textContent = '🎤 语音';
        voiceBtn.classList.remove('voice-recording');
        showToast('语音识别失败，请重试');
    };

    recognition.onend = () => {
        voiceBtn.textContent = '🎤 语音';
        voiceBtn.classList.remove('voice-recording');
    };

    recognition.start();
}

// ==================== 用户画像 ====================
async function loadProfile() {
    try {
        const res = await fetch(`${API_BASE}/api/recipes/profile`);
        const data = await res.json();
        if (data.success) {
            updateProfileDisplay(data.data);
        }
    } catch (e) {
        console.log('加载画像失败', e);
    }
}

function updateProfileDisplay(profile) {
    const container = document.getElementById('profile-display');
    const tags = [];
    if (profile.taste && profile.taste !== '不限制') tags.push(`口味：${profile.taste}`);
    if (profile.goal && profile.goal !== '无特殊') tags.push(`目标：${profile.goal}`);
    if (profile.max_time && profile.max_time !== '不限制') tags.push(`时长：${profile.max_time}`);
    if (!tags.length) tags.push('口味：不限制', '目标：无特殊');

    container.innerHTML = tags.map(t =>
        `<span class="bg-white px-2 py-1 rounded-full text-gray-600 border text-xs">${t}</span>`
    ).join('');
}

function showProfileModal() {
    document.getElementById('profile-modal').classList.remove('hidden');
}

async function saveProfile() {
    const profile = {
        taste: document.getElementById('profile-taste').value,
        goal: document.getElementById('profile-goal').value,
        max_time: document.getElementById('profile-time').value,
        staples: document.getElementById('profile-staples').value.split(/[,，]/).map(s => s.trim()).filter(Boolean)
    };

    try {
        const res = await fetch(`${API_BASE}/api/recipes/profile`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(profile)
        });
        const data = await res.json();
        if (data.success) {
            updateProfileDisplay(data.data);
            closeModal('profile-modal');
            showToast('偏好已保存');
        }
    } catch (e) {
        showToast('保存失败');
    }
}

// ==================== 菜谱推荐 ====================
async function getRecommendations() {
    if (!currentIngredients.length) {
        showToast('请先拍照或添加食材');
        return;
    }

    const names = currentIngredients.map(i => i.name);
    try {
        const res = await fetch(`${API_BASE}/api/recipes/recommend`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ingredients: names })
        });
        const data = await res.json();

        if (!data.success) {
            showToast(data.error);
            return;
        }

        currentRecipes = data.data || [];
        renderRecipes();
        showSection('recipes-section');
        showToast(`为你推荐 ${currentRecipes.length} 道菜`);

    } catch (e) {
        showToast('获取推荐失败');
    }
}

function renderRecipes() {
    const container = document.getElementById('recipes-list');
    const countEl = document.getElementById('recipe-count');
    container.innerHTML = '';
    countEl.textContent = `共 ${currentRecipes.length} 道`;

    currentRecipes.forEach(recipe => {
        const card = document.createElement('div');
        card.className = 'recipe-card';

        const matchClass = recipe.match_score >= 0.8 ? 'match-high' : recipe.match_score >= 0.6 ? 'match-medium' : 'match-low';
        const haveItems = recipe.ingredients.filter(i => i.has);
        const missItems = recipe.ingredients.filter(i => !i.has);

        card.innerHTML = `
            <div class="flex justify-between items-start mb-2">
                <div>
                    <h3 class="font-bold text-gray-800">${recipe.name}</h3>
                    <div class="flex gap-2 mt-1 text-xs text-gray-500">
                        <span>⏱️ ${recipe.time}</span>
                        <span>📊 ${recipe.difficulty}</span>
                    </div>
                </div>
                <span class="match-badge ${matchClass}">${Math.round(recipe.match_score * 100)}% 匹配</span>
            </div>
            <p class="text-xs text-emerald-600 mb-2">💡 ${recipe.reason}</p>
            <div class="space-y-1">
                ${haveItems.map(i => `<div class="ingredient-status"><span class="check">✓</span><span class="text-gray-600">${i.name} ${i.amount}</span></div>`).join('')}
                ${missItems.slice(0, 2).map(i => `<div class="ingredient-status"><span class="cross">✗</span><span class="text-gray-400">${i.name} ${i.amount}</span></div>`).join('')}
                ${missItems.length > 2 ? `<div class="text-xs text-gray-400 pl-5">还有 ${missItems.length - 2} 种缺料...</div>` : ''}
            </div>
        `;

        card.onclick = () => showRecipeDetail(recipe);
        container.appendChild(card);
    });
}

function showRecipeDetail(recipe) {
    currentRecipeDetail = recipe;
    document.getElementById('recipe-modal-title').textContent = recipe.name;

    const content = document.getElementById('recipe-modal-content');
    const haveItems = recipe.ingredients.filter(i => i.has);
    const missItems = recipe.ingredients.filter(i => !i.has);

    content.innerHTML = `
        <div class="flex gap-2 text-xs text-gray-500 mb-3">
            ${recipe.tags.map(t => `<span class="bg-gray-100 px-2 py-1 rounded-full">${t}</span>`).join('')}
        </div>
        <div class="mb-4">
            <h4 class="font-bold text-sm text-gray-700 mb-2">🥬 所需食材</h4>
            <div class="space-y-1">
                ${haveItems.map(i => `<div class="ingredient-status"><span class="check">✓</span><span class="text-gray-700">${i.name} <span class="text-gray-400">${i.amount}</span></span></div>`).join('')}
                ${missItems.map(i => `<div class="ingredient-status"><span class="cross">✗</span><span class="text-gray-700">${i.name} <span class="text-gray-400">${i.amount}</span></span></div>`).join('')}
            </div>
        </div>
        <div>
            <h4 class="font-bold text-sm text-gray-700 mb-2">👨‍🍳 烹饪步骤</h4>
            <ol class="step-list">
                ${recipe.steps.map(s => `<li>${s}</li>`).join('')}
            </ol>
        </div>
    `;

    document.getElementById('recipe-modal').classList.remove('hidden');
}

// ==================== 反向查询 ====================
async function checkDish() {
    const dishName = document.getElementById('search-dish').value.trim();
    if (!dishName) {
        showToast('请输入菜名');
        return;
    }

    const names = currentIngredients.map(i => i.name);
    try {
        const res = await fetch(`${API_BASE}/api/recipes/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dish_name: dishName, ingredients: names })
        });
        const data = await res.json();

        const resultEl = document.getElementById('search-result');
        resultEl.classList.remove('hidden');

        if (!data.success) {
            resultEl.innerHTML = `<div class="text-red-500 text-sm">查询失败</div>`;
            return;
        }

        const d = data.data;
        if (!d.found) {
            resultEl.innerHTML = `<div class="bg-gray-50 rounded-xl p-4 text-sm text-gray-600">${d.message}</div>`;
            return;
        }

        resultEl.innerHTML = `
            <div class="bg-white rounded-xl border border-gray-100 p-4">
                <div class="flex justify-between items-center mb-2">
                    <h4 class="font-bold">${d.dish}</h4>
                    <span class="text-xs ${d.match_score >= 0.8 ? 'text-emerald-600' : 'text-amber-600'}">匹配度 ${Math.round(d.match_score * 100)}%</span>
                </div>
                <div class="mb-2">
                    <p class="text-xs text-gray-500 mb-1">✅ 已有食材（${d.have.length}种）</p>
                    <div class="flex flex-wrap gap-1">${d.have.map(h => `<span class="text-xs bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full">${h}</span>`).join('')}</div>
                </div>
                <div class="mb-2">
                    <p class="text-xs text-gray-500 mb-1">❌ 缺料（${d.missing.length}种）</p>
                    <div class="flex flex-wrap gap-1">${d.missing.map(m => `<span class="text-xs bg-red-50 text-red-700 px-2 py-0.5 rounded-full">${m}</span>`).join('')}</div>
                </div>
            </div>
        `;
    } catch (e) {
        showToast('查询失败');
    }
}

// ==================== 购物清单 ====================
function addToShoppingListFromModal() {
    if (!currentRecipeDetail) return;

    const missing = currentRecipeDetail.ingredients.filter(i => !i.has);
    missing.forEach(item => {
        const existing = shoppingList.find(s => s.name === item.name);
        if (!existing) {
            shoppingList.push({
                name: item.name,
                amount: item.amount,
                for_dishes: [currentRecipeDetail.name],
                checked: false
            });
        } else if (!existing.for_dishes.includes(currentRecipeDetail.name)) {
            existing.for_dishes.push(currentRecipeDetail.name);
        }
    });

    closeModal('recipe-modal');
    showShoppingList();
    showToast(`已添加 ${missing.length} 种食材到购物清单`);
}

function showShoppingList() {
    const container = document.getElementById('shopping-list');

    if (!shoppingList.length) {
        container.innerHTML = `<div class="text-center text-gray-400 text-sm py-4">🛒 购物清单为空<br><span class="text-xs">点击菜谱中的"+清单"添加</span></div>`;
    } else {
        container.innerHTML = shoppingList.map((item, idx) => `
            <div class="flex items-center gap-3 py-2 ${item.checked ? 'opacity-50' : ''}">
                <input type="checkbox" ${item.checked ? 'checked' : ''} onchange="toggleShoppingItem(${idx})" class="w-4 h-4 accent-emerald-500">
                <div class="flex-1">
                    <p class="text-sm font-medium ${item.checked ? 'line-through text-gray-400' : 'text-gray-700'}">${item.name}</p>
                    <p class="text-xs text-gray-400">${item.amount} · 用于：${item.for_dishes.join('、')}</p>
                </div>
                <button onclick="removeShoppingItem(${idx})" class="text-gray-400 hover:text-red-500 text-sm">×</button>
            </div>
        `).join('');
    }

    showSection('shopping-section');
    scrollToSection('shopping-section');
}

function toggleShoppingItem(idx) {
    shoppingList[idx].checked = !shoppingList[idx].checked;
    showShoppingList();
}

function removeShoppingItem(idx) {
    shoppingList.splice(idx, 1);
    showShoppingList();
}

function copyShoppingList() {
    if (!shoppingList.length) {
        showToast('清单为空');
        return;
    }
    const text = '【Bonnie Fridge 购物清单】\n' +
        shoppingList.filter(s => !s.checked).map(s => `□ ${s.name} ${s.amount}`).join('\n');

    navigator.clipboard.writeText(text).then(() => {
        showToast('购物清单已复制到剪贴板');
    }).catch(() => {
        showToast('复制失败');
    });
}

// ==================== 做菜扣减库存 ====================
async function cookThisDish() {
    if (!currentRecipeDetail) return;

    const used = currentRecipeDetail.ingredients
        .filter(i => i.has)
        .map(i => ({ name: i.name, quantity: i.amount }));

    try {
        const res = await fetch(`${API_BASE}/api/ingredients/consume`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(used)
        });
        const data = await res.json();

        if (data.success) {
            currentIngredients = data.data;
            renderIngredients();
            closeModal('recipe-modal');
            showToast(`已扣除 ${used.length} 种食材库存，祝你烹饪愉快！🍳`);
        }
    } catch (e) {
        showToast('扣减库存失败');
    }
}

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    loadProfile();
});
