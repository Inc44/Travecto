let lastPlan = null;

function populateDays(resp)
{
	const day = document.getElementById('day');
	day.innerHTML = '';
	resp.routes.forEach((info, i) =>
	{
		const option = document.createElement('option');
		option.value = i;
		option.textContent = info.day ? `Day ${info.day}` : 'Route';
		day.appendChild(option);
	});
}

function renderList(resp)
{
	const list = document.getElementById('list');
	list.innerHTML = '';
	resp.routes.forEach(info =>
	{
		list.insertAdjacentHTML('beforeend', `
			<h2>${info.day ? `Day ${info.day}` : 'Route'}</h2>
			<ol>${info.places.map(place => `<li>${place}</li>`).join('')}</ol>
			<p>${(info.distance_m / 1000).toFixed(1)} km | ${info.time_minutes} min</p>
		`);
	});
}

function showMap(idx)
{
	document.getElementById('mapFrame')
		.src = lastPlan.routes[idx].map_path;
}

function updateView()
{
	const view = document.getElementById('view')
		.value;
	const list = document.getElementById('list');
	const map = document.getElementById('map');
	const day = document.getElementById('day');
	const mandatory = lastPlan.routes.some(route => route.day != null);
	list.classList.toggle('hidden', view !== 'list');
	map.classList.toggle('hidden', view !== 'map');
	day.classList.toggle('hidden', !(view === 'map' && mandatory));
	if (!lastPlan) return;
	if (view === 'list') renderList(lastPlan);
	else showMap(mandatory ? day.value : 0);
}
document.querySelector('h1')
	.addEventListener('click', () =>
	{
		const isDarkMode = document.body.classList.toggle('dark');
		localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
	});
document.getElementById('view')
	.addEventListener('change', updateView);
document.getElementById('day')
	.addEventListener('change', event => showMap(event.target.value));
['home', 'places', 'mandatory', 'altAddresses'].forEach(id =>
{
	document.getElementById(id)
		.addEventListener('input', event => localStorage.setItem(id, event.target.value));
});
document.getElementById('mode')
	.addEventListener('change', event => localStorage.setItem('mode', event.target.value));
document.getElementById('view')
	.addEventListener('change', event => localStorage.setItem('view', event.target.value));

function restoreForm()
{
	const params = new URLSearchParams(window.location.search);
	let hadParams = false;

	function setValue(id)
	{
		const value = params.get(id);
		if (value !== null)
		{
			document.getElementById(id)
				.value = value;
			localStorage.setItem(id, value);
			hadParams = true;
		}
		else
		{
			const value = localStorage.getItem(id);
			if (value !== null) document.getElementById(id)
				.value = value;
		}
	}
	setValue('home');
	setValue('places');
	setValue('mandatory');
	setValue('altAddresses');
	setValue('mode');
	setValue('view');
	const theme = localStorage.getItem('theme');
	if (theme === 'dark') document.body.classList.add('dark');
	else document.body.classList.remove('dark');
	updateView();
	if (hadParams) window.history.replaceState(null, '', window.location.pathname + window.location.hash);
}
async function plan()
{
	document.getElementById('list')
		.innerHTML = '';
	document.getElementById('mapFrame')
		.src = '';
	const home = document.getElementById('home')
		.value.trim();
	const places = document.getElementById('places')
		.value.split(/\r?\n/)
		.map(line => line.trim())
		.filter(Boolean);
	const mandatoryLines = document.getElementById('mandatory')
		.value.split(/\r?\n/)
		.map(line => line.trim())
		.filter(Boolean);
	const mandatory = {};
	mandatoryLines.forEach(mandatoryLine =>
	{
		const [day, places] = mandatoryLine.split('|');
		if (!day || !places) return;
		places.split(',')
			.forEach(place =>
			{
				place = place.trim();
				if (place)(mandatory[day] ??= [])
					.push(place);
			});
	});
	const altAdressesLines = document.getElementById('altAddresses')
		.value.split(/\r?\n/)
		.map(line => line.trim())
		.filter(Boolean);
	const altAddresses = {};
	altAdressesLines.forEach(altAdressesLine =>
	{
		const [original, ...replacement] = altAdressesLine.split('|');
		if (original) altAddresses[original.trim()] = replacement.join('|')
			.trim();
	});
	const payload = {
		city_name: 'custom',
		config:
		{
			home: home || null,
			places,
			mandatory_by_day: mandatory,
			alt_addresses: altAddresses,
			mode: document.getElementById('mode')
				.value
		}
	};
	try
	{
		const resp = await fetch('/plan',
		{
			method: 'POST',
			headers:
			{
				'Content-Type': 'application/json'
			},
			body: JSON.stringify(payload)
		});
		if (!resp.ok) throw new Error(await resp.text());
		lastPlan = await resp.json();
		populateDays(lastPlan);
		document.getElementById('day')
			.value = 0;
		updateView();
	}
	catch (e)
	{
		alert('Planning failed: ' + e.message);
	}
}

function share()
{
	const url = new URL(window.location.href);
	const params = url.searchParams;
	params.set('home', document.getElementById('home')
		.value.trim());
	params.set('places', document.getElementById('places')
		.value);
	params.set('mandatory', document.getElementById('mandatory')
		.value);
	params.set('altAddresses', document.getElementById('altAddresses')
		.value);
	params.set('mode', document.getElementById('mode')
		.value);
	params.set('view', document.getElementById('view')
		.value);
	url.search = params.toString();
	navigator.clipboard.writeText(url.toString());
}
document.getElementById('plan')
	.addEventListener('click', plan);
document.getElementById('share')
	.addEventListener('click', share);
restoreForm()