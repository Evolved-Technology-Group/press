<!--
  Yukon HQ settings.

  HQ Settings is a Single, so it has no list and does not fit the dashboard's
  object system — hence a page rather than an object definition.

  Sections mirror the doctype rather than inventing a new grouping, so an
  operator who has used the desk form finds the same things in the same order.
  Passwords are write-only: Frappe will not hand back a stored secret, so an
  empty box means "unchanged", never "blank".
-->
<template>
	<div class="p-5">
		<Breadcrumbs :items="[{ label: 'HQ Settings', route: '/hq/settings' }]" />

		<div v-if="settings.doc" class="mt-5 max-w-3xl space-y-8">
			<section v-for="section in SECTIONS" :key="section.label">
				<h2 class="text-lg font-medium text-ink-gray-9">{{ section.label }}</h2>
				<p v-if="section.description" class="mt-1 text-p-sm text-ink-gray-6">
					{{ section.description }}
				</p>

				<div class="mt-4 space-y-4">
					<div v-for="field in section.fields" :key="field.fieldname">
						<FormControl
							:type="controlType(field)"
							:label="field.label"
							:options="field.options"
							:modelValue="valueFor(field)"
							:placeholder="field.type === 'password' ? 'unchanged' : ''"
							@update:modelValue="(value) => stage(field, value)"
						/>
						<p v-if="field.description" class="mt-1 text-p-xs text-ink-gray-5">
							{{ field.description }}
						</p>
					</div>
				</div>
			</section>

			<div class="flex items-center gap-3 border-t border-outline-gray-1 pt-5">
				<Button
					variant="solid"
					:loading="settings.setValue.loading"
					:disabled="!isDirty"
					@click="save"
				>
					Save
				</Button>
				<Button v-if="isDirty" @click="staged = {}">Discard</Button>
				<span v-if="isDirty" class="text-p-sm text-ink-gray-6">
					{{ Object.keys(staged).length }} unsaved change(s)
				</span>
			</div>
		</div>

		<div v-else class="mt-5 text-p-sm text-ink-gray-6">Loading settings…</div>
	</div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { Breadcrumbs, Button, FormControl, createDocumentResource } from 'frappe-ui';
import { toast } from 'vue-sonner';

const DAYS = [
	'Monday',
	'Tuesday',
	'Wednesday',
	'Thursday',
	'Friday',
	'Saturday',
	'Sunday',
];

// Ordered to match the doctype. Every field an operator is expected to set —
// read-only and derived values live on the records themselves, not here.
const SECTIONS = [
	{
		label: 'Tenant app bundles',
		fields: [
			{ fieldname: 'default_crm_app_bundle', label: 'Default CRM app bundle' },
			{ fieldname: 'default_erp_app_bundle', label: 'Default ERP app bundle' },
		],
	},
	{
		label: 'Fleet patching',
		description:
			'The weekly reboot window. Keep clear of 03:20 (control-plane backup) and 04:00 (site backups).',
		fields: [
			{ fieldname: 'patching_enabled', label: 'Patching enabled', type: 'checkbox' },
			{
				fieldname: 'maintenance_day',
				label: 'Maintenance day',
				type: 'select',
				options: DAYS,
			},
			{ fieldname: 'maintenance_hour_utc', label: 'Maintenance hour (UTC)', type: 'number' },
			{ fieldname: 'reboot_wait_seconds', label: 'Reboot wait (seconds)', type: 'number' },
			{
				fieldname: 'patch_control_plane',
				label: 'Include the control plane',
				type: 'checkbox',
				description: 'Leave off — press-hq cannot orchestrate its own reboot.',
			},
		],
	},
	{
		label: 'Alert routing',
		description:
			'Critical alerts are delivered as they are raised. Warnings stay in the alert list.',
		fields: [
			{ fieldname: 'alert_email', label: 'Alert email' },
			{
				fieldname: 'telegram_chat_id',
				label: 'Telegram chat id',
				description: 'Needs a bot token beside it — either alone routes nothing.',
			},
			{ fieldname: 'telegram_bot_token', label: 'Telegram bot token', type: 'password' },
			{
				fieldname: 'site_notification_email',
				label: 'Site notification email',
				description:
					'Written onto every new site. Press aborts Login as Administrator when no recipient resolves.',
			},
			{
				fieldname: 'fleet_team',
				label: 'Fleet team',
				description:
					'The press Team that owns what HQ creates. Blank keeps the Administrator-owned team.',
			},
		],
	},
	{
		label: 'Commissioned storage',
		description:
			'Backblaze B2, Canada East. The ceiling is base + (seats × per-seat) + (blocks × block size).',
		fields: [
			{ fieldname: 'b2_key_id', label: 'Backblaze key ID' },
			{ fieldname: 'b2_application_key', label: 'Backblaze application key', type: 'password' },
			{ fieldname: 'storage_base_gb', label: 'Base storage (GB)', type: 'number' },
			{ fieldname: 'storage_gb_per_seat', label: 'Storage per seat (GB)', type: 'number' },
			{ fieldname: 'storage_block_gb', label: 'Block size (GB)', type: 'number' },
			{
				fieldname: 'storage_auto_block_limit',
				label: 'Auto-grant limit (blocks)',
				type: 'number',
				description:
					'Most blocks HQ will grant and bill for one tenant on its own. 0 removes the bound.',
			},
		],
	},
	{
		label: 'HaloPSA',
		fields: [
			{ fieldname: 'halo_resource_url', label: 'Resource URL' },
			{ fieldname: 'halo_auth_url', label: 'Auth URL' },
			{ fieldname: 'halo_client_id', label: 'Client id' },
			{ fieldname: 'halo_client_secret', label: 'Client secret', type: 'password' },
			{ fieldname: 'halo_ticket_type_id', label: 'Ticket type id' },
			{ fieldname: 'halo_ticket_url_template', label: 'Ticket URL template' },
			{ fieldname: 'halo_priority_ids', label: 'Priority ids (JSON)', type: 'textarea' },
		],
	},
	{
		label: 'System sender (SMTP)',
		description:
			'One fleet-wide SMTP user, published to every tenant as mail_* site config. Port 465 will not work — use 587, 2525 or 8025.',
		fields: [
			{ fieldname: 'system_smtp_host', label: 'SMTP host' },
			{ fieldname: 'system_smtp_port', label: 'SMTP port', type: 'number' },
			{ fieldname: 'system_smtp_login', label: 'SMTP username' },
			{ fieldname: 'system_smtp_password', label: 'SMTP password', type: 'password' },
			{ fieldname: 'system_smtp_use_tls', label: 'Use STARTTLS', type: 'checkbox' },
			{ fieldname: 'system_sender_domain', label: 'Sender domain' },
			{ fieldname: 'system_sender_local_part', label: 'Sender local part' },
			{ fieldname: 'system_sender_name', label: 'Sender display name' },
		],
	},
	{
		label: 'Yukon Send',
		fields: [{ fieldname: 'smtp2go_api_key', label: 'SMTP2GO master API key', type: 'password' }],
	},
	{
		label: 'Microsoft 365',
		fields: [
			{ fieldname: 'm365_client_id', label: 'Client id' },
			{ fieldname: 'm365_relay_url', label: 'Relay URL' },
			{ fieldname: 'm365_relay_master_secret', label: 'Relay master secret', type: 'password' },
		],
	},
	{
		label: 'DigitalOcean',
		fields: [{ fieldname: 'digitalocean_project_id', label: 'Project id' }],
	},
];

const settings = createDocumentResource({
	doctype: 'HQ Settings',
	name: 'HQ Settings',
	auto: true,
});

const staged = ref({});
const isDirty = computed(() => Object.keys(staged.value).length > 0);

function controlType(field) {
	return field.type || 'text';
}

/**
 * A staged edit wins; otherwise the stored value.
 *
 * Passwords never render their stored value — Frappe will not return one, and
 * showing a masked placeholder as if it were the secret invites someone to
 * "correct" it and overwrite a working credential with asterisks.
 */
function valueFor(field) {
	if (field.fieldname in staged.value) return staged.value[field.fieldname];
	if (field.type === 'password') return '';
	return settings.doc?.[field.fieldname] ?? '';
}

function stage(field, value) {
	staged.value = { ...staged.value, [field.fieldname]: value };
}

function save() {
	const values = { ...staged.value };
	// An untouched password box is "unchanged", not "clear it".
	for (const section of SECTIONS) {
		for (const field of section.fields) {
			if (field.type === 'password' && values[field.fieldname] === '') {
				delete values[field.fieldname];
			}
		}
	}
	if (!Object.keys(values).length) {
		staged.value = {};
		return;
	}
	return settings.setValue.submit(values, {
		onSuccess: () => {
			staged.value = {};
			toast.success('Settings saved');
		},
		onError: (error) => toast.error(error?.messages?.[0] || 'Could not save settings'),
	});
}
</script>
