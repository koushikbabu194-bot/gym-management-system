const api = path => fetch(path).then(response => response.json());
const $ = id => document.getElementById(id);

document.querySelectorAll(".tab").forEach(button => {
  button.onclick = () => {
    document.querySelectorAll(".tab, .page").forEach(item => {
      item.classList.remove("active");
    });

    button.classList.add("active");
    $(button.dataset.tab).classList.add("active");
  };
});

async function loadStats() {
  const stats = await api("/api/stats");

  $("s-members").textContent = stats.members;
  $("s-present").textContent = stats.present_today;
  $("s-paid").textContent = stats.paid;
  $("s-revenue").textContent = "₹" + stats.revenue;
}

async function loadMembers() {
  const members = await api("/api/members");

  $("members-table").querySelector("tbody").innerHTML = members.map(member => `
    <tr>
      <td>${member.name}</td>
      <td>${member.phone || "-"}</td>
      <td>${member.plan}</td>
      <td>${member.join_date}</td>
      <td>${member.fee_status}</td>
      <td>
        <button class="delete" onclick="deleteMember('${member.id}')">
          Delete
        </button>
      </td>
    </tr>
  `).join("");

  const options = members.map(member => `
    <option value="${member.id}">${member.name}</option>
  `).join("");

  $("a-member").innerHTML = options;
  $("p-member").innerHTML = options;
}

async function loadAttendance() {
  const records = await api("/api/attendance");

  $("attendance-table").querySelector("tbody").innerHTML = records.map(record => `
    <tr>
      <td>${record.name}</td>
      <td>${record.checkin_date}</td>
      <td>${record.checkin_time}</td>
    </tr>
  `).join("");
}

async function loadPayments() {
  const records = await api("/api/payments");

  $("payments-table").querySelector("tbody").innerHTML = records.map(record => `
    <tr>
      <td>${record.name}</td>
      <td>₹${record.amount}</td>
      <td>${record.pay_date}</td>
      <td>${record.method}</td>
    </tr>
  `).join("");
}

$("member-form").onsubmit = async event => {
  event.preventDefault();

  await fetch("/api/members", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: $("m-name").value,
      phone: $("m-phone").value,
      email: $("m-email").value,
      plan: $("m-plan").value
    })
  });

  event.target.reset();
  refresh();
};

$("attendance-form").onsubmit = async event => {
  event.preventDefault();

  await fetch("/api/attendance", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      member_id: $("a-member").value
    })
  });

  refresh();
};

$("payment-form").onsubmit = async event => {
  event.preventDefault();

  await fetch("/api/payments", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      member_id: $("p-member").value,
      amount: $("p-amount").value,
      method: $("p-method").value
    })
  });

  event.target.reset();
  refresh();
};

async function deleteMember(id) {
  if (!confirm("Delete this member?")) return;

  await fetch("/api/members/" + id, {
    method: "DELETE"
  });

  refresh();
}

function refresh() {
  loadStats();
  loadMembers();
  loadAttendance();
  loadPayments();
}

refresh();