const API_URL = window.location.origin.startsWith('http') ? window.location.origin : 'http://localhost:8000';
let currentToken = localStorage.getItem('token');
let currentUser = null;

// UI Helpers
function showModal(id) { document.getElementById(id).classList.add('active'); }
function closeModal(id) { document.getElementById(id).classList.remove('active'); }
function switchView(viewId) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');
}

// Initialization
async function init() {
    if (currentToken) {
        await fetchCurrentUser();
    }
}

async function fetchCurrentUser() {
    try {
        const res = await fetch(`${API_URL}/me`, {
            headers: { 'Authorization': `Bearer ${currentToken}` }
        });
        if (!res.ok) throw new Error("Invalid token");
        currentUser = await res.json();
        
        document.getElementById('authButtons').style.display = 'none';
        document.getElementById('userMenu').style.display = 'flex';
        document.getElementById('userNameDisplay').innerText = `Hello, ${currentUser.full_name}`;
        
        if (currentUser.role === 'FARMER') {
            switchView('farmerDashboardView');
            loadFarmerData();
        } else if (currentUser.role === 'ADMIN') {
            switchView('adminDashboardView');
            loadAdminData();
        }
    } catch (e) {
        console.error(e);
        logout();
    }
}

function logout() {
    localStorage.removeItem('token');
    currentToken = null;
    currentUser = null;
    document.getElementById('authButtons').style.display = 'flex';
    document.getElementById('userMenu').style.display = 'none';
    switchView('landingView');
}

// Auth API Calls
async function registerFarmer() {
    const regErr = document.getElementById('regError');
    if (regErr) regErr.style.display = 'none';

    const aadhaar = document.getElementById('regAadhaar').value.trim();
    const name = document.getElementById('regName').value.trim();
    const phone = document.getElementById('regPhone').value.trim();
    const password = document.getElementById('regPassword').value;

    if (!aadhaar || aadhaar.length !== 12 || !/^\d+$/.test(aadhaar)) {
        if (regErr) { regErr.innerText = "Please enter a valid 12-digit Aadhaar number."; regErr.style.display = 'block'; }
        else alert("Please enter a valid 12-digit Aadhaar number.");
        return;
    }
    if (!name) {
        if (regErr) { regErr.innerText = "Please enter your full name."; regErr.style.display = 'block'; }
        else alert("Please enter your full name.");
        return;
    }
    if (!password) {
        if (regErr) { regErr.innerText = "Please enter a password."; regErr.style.display = 'block'; }
        else alert("Please enter a password.");
        return;
    }

    const data = {
        aadhaar_number: aadhaar,
        full_name: name,
        phone: phone,
        password: password
    };

    try {
        const res = await fetch(`${API_URL}/register/farmer`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            alert("Registration successful! Please login with your Aadhaar and Password.");
            closeModal('registerModal');
            document.getElementById('loginId').value = aadhaar;
            document.getElementById('loginPassword').value = '';
            showModal('loginModal');
        } else {
            const err = await res.json();
            const msg = "Registration Failed: " + (err.detail || "Unable to register");
            if (regErr) { regErr.innerText = msg; regErr.style.display = 'block'; }
            else alert(msg);
        }
    } catch (e) {
        if (regErr) { regErr.innerText = "Connection error. Please try again."; regErr.style.display = 'block'; }
        else alert("Connection error. Please try again.");
    }
}

async function login() {
    const loginErr = document.getElementById('loginError');
    if (loginErr) loginErr.style.display = 'none';

    const loginId = document.getElementById('loginId').value.trim();
    const password = document.getElementById('loginPassword').value;

    if (!loginId || !password) {
        if (loginErr) { loginErr.innerText = "Please enter both Aadhaar/Username and Password."; loginErr.style.display = 'block'; }
        else alert("Please enter both Aadhaar/Username and Password.");
        return;
    }

    const formData = new URLSearchParams();
    formData.append('username', loginId);
    formData.append('password', password);
    
    try {
        const res = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData
        });
        if (res.ok) {
            const data = await res.json();
            localStorage.setItem('token', data.access_token);
            currentToken = data.access_token;
            closeModal('loginModal');
            await fetchCurrentUser();
        } else {
            const err = await res.json();
            const msg = "Login Failed: " + (err.detail || "Invalid Aadhaar/Username or Password");
            if (loginErr) { loginErr.innerText = msg; loginErr.style.display = 'block'; }
            else alert(msg);
        }
    } catch (e) {
        if (loginErr) { loginErr.innerText = "Connection error. Please try again."; loginErr.style.display = 'block'; }
        else alert("Connection error. Please try again.");
    }
}

// Farmer Functions
async function loadFarmerData() {
    let landAcres = 0;
    if (currentUser.profile) {
        landAcres = currentUser.profile.land_area_acres || 0;
        document.getElementById('farmerLandArea').innerText = landAcres;
        document.getElementById('farmerMaxWeight').innerText = (landAcres * 10).toFixed(1);
        document.getElementById('farmerTotalRevenue').innerText = currentUser.profile.total_revenue;
    }
    
    // 1st Time Login Rule: If land_area_acres is 0 / not registered, automatically show prompt!
    if (!landAcres || landAcres <= 0) {
        document.getElementById('landModalTitle').innerText = "Register Land Details (First-Time Setup)";
        showModal('updateProfileModal');
        document.getElementById('maxLimitNotice').innerText = "⚠️ Please register your land area details above to enable slot booking.";
        document.getElementById('cropQuantity').value = '';
    } else {
        // Land details provided -> Skip modal prompt automatically on login!
        const maxWeight = (landAcres * 10).toFixed(1);
        const qtyInput = document.getElementById('cropQuantity');
        qtyInput.value = maxWeight; // Default value set to max allowed weight (land_area_acres * 10)
        qtyInput.setAttribute('max', maxWeight);
        document.getElementById('maxLimitNotice').innerText = `💡 Maximum Limit: ${maxWeight} Quintals (${landAcres} Acres × 10 Qtl/Acre). You can decrease the amount if needed.`;
    }
    
    // Load crops for select
    const cropRes = await fetch(`${API_URL}/crops`);
    const crops = await cropRes.json();
    const select = document.getElementById('cropSelect');
    select.innerHTML = '';
    crops.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.id;
        opt.innerText = `${c.name} - ₹${c.price_per_quintal}/qtl`;
        select.appendChild(opt);
    });

    // Load history
    const histRes = await fetch(`${API_URL}/farmer/history`, {
        headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    const history = await histRes.json();
    const tbody = document.getElementById('farmerHistoryTable');
    tbody.innerHTML = '';

    const currentYear = new Date().getFullYear();
    let hasBookedThisYear = false;

    history.forEach(tx => {
        const txYear = new Date(tx.created_at).getFullYear();
        if (txYear === currentYear) {
            hasBookedThisYear = true;
        }

        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${new Date(tx.created_at).toLocaleDateString()}</td>
            <td>${tx.crop.name}</td>
            <td>${tx.quantity_quintals}</td>
            <td>₹${tx.amount_calculated}</td>
            <td>${tx.slot ? `Date: ${new Date(tx.slot.scheduled_date).toLocaleDateString()} (Q#${tx.slot.queue_number}) - ${tx.status}` : tx.status}</td>
        `;
        tbody.appendChild(tr);
    });

    // Rule: Annual slot booking capping (1 booking per farmer per year)
    const annualNotice = document.getElementById('annualLimitNotice');
    const bookBtn = document.getElementById('bookSlotBtn');
    if (hasBookedThisYear) {
        annualNotice.style.display = 'block';
        annualNotice.innerText = `⚠️ Annual Limit Reached: You have already booked your slot for ${currentYear}. Government policy permits 1 slot per farmer per year.`;
        bookBtn.disabled = true;
        bookBtn.style.opacity = '0.5';
        bookBtn.style.cursor = 'not-allowed';
    } else {
        annualNotice.style.display = 'none';
        bookBtn.disabled = false;
        bookBtn.style.opacity = '1';
        bookBtn.style.cursor = 'pointer';
    }
}

async function updateProfile() {
    const area = document.getElementById('updateLandArea').value;
    if (!area || parseFloat(area) <= 0) return alert("Please enter a valid land area in Acres");

    const res = await fetch(`${API_URL}/farmer/profile`, {
        method: 'PUT',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${currentToken}` 
        },
        body: JSON.stringify({ land_area_acres: parseFloat(area) })
    });
    if (res.ok) {
        closeModal('updateProfileModal');
        await fetchCurrentUser();
    } else {
        const err = await res.json();
        alert("Error: " + (err.detail || "Failed to update profile"));
    }
}

async function bookSlot() {
    const crop_id = document.getElementById('cropSelect').value;
    const qty = document.getElementById('cropQuantity').value;
    
    if(!crop_id || !qty) return alert("Please fill all fields");

    const landAcres = currentUser.profile ? (currentUser.profile.land_area_acres || 0) : 0;
    if (!landAcres || landAcres <= 0) {
        showModal('updateProfileModal');
        return alert("Please register your land area details first!");
    }

    const maxWeight = landAcres * 10;
    if (parseFloat(qty) > maxWeight) {
        return alert(`Maximum Quantity Exceeded!\nBased on your land area (${landAcres} Acres), you can sell at most ${maxWeight} Quintals.`);
    }

    const res = await fetch(`${API_URL}/farmer/book-slot`, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${currentToken}` 
        },
        body: JSON.stringify({ crop_id: parseInt(crop_id), quantity_quintals: parseFloat(qty) })
    });
    
    if (res.ok) {
        document.getElementById('bookingMessage').innerText = "✅ Slot booked successfully!";
        await loadFarmerData(); // Refresh history and apply annual capping
    } else {
        const err = await res.json();
        alert("Booking Failed: " + (err.detail || "Unable to book slot"));
    }
}

// Admin Functions
async function loadAdminData() {
    const cropRes = await fetch(`${API_URL}/crops`);
    const crops = await cropRes.json();
    const tbody = document.getElementById('adminCropTable');
    tbody.innerHTML = '';
    crops.forEach(c => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${c.name}</td>
            <td><input type="number" value="${c.price_per_quintal}" id="crop-price-${c.id}"></td>
            <td><button class="secondary" onclick="updateCropPrice(${c.id})">Update</button></td>
        `;
        tbody.appendChild(tr);
    });

    const slotRes = await fetch(`${API_URL}/admin/slots`, {
        headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    const slots = await slotRes.json();
    const stbody = document.getElementById('adminSlotsTable');
    stbody.innerHTML = '';
    slots.forEach(s => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${s.id}</td>
            <td>${new Date(s.scheduled_date).toLocaleDateString()} (Q#${s.queue_number})</td>
            <td>TransID: ${s.transaction_id}</td>
            <td>${s.status}</td>
            <td>
                ${s.status === 'PENDING' ? `<button class="primary" onclick="completeSlot(${s.id})">Mark Complete</button>` : 'Done'}
            </td>
        `;
        stbody.appendChild(tr);
    });
}

async function addCrop() {
    const name = document.getElementById('newCropName').value;
    const price = document.getElementById('newCropPrice').value;
    
    const res = await fetch(`${API_URL}/admin/crops`, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${currentToken}` 
        },
        body: JSON.stringify({ name, price_per_quintal: parseFloat(price) })
    });
    if (res.ok) {
        document.getElementById('newCropName').value = '';
        document.getElementById('newCropPrice').value = '';
        loadAdminData();
    }
}

async function updateCropPrice(id) {
    const price = document.getElementById(`crop-price-${id}`).value;
    await fetch(`${API_URL}/admin/crops/${id}`, {
        method: 'PUT',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${currentToken}` 
        },
        body: JSON.stringify({ price_per_quintal: parseFloat(price) })
    });
    loadAdminData();
}

async function completeSlot(id) {
    await fetch(`${API_URL}/admin/slots/${id}/complete`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    loadAdminData();
}

// Run init on load
init();
