// Yukon HQ — tenants.
//
// The business record wrapped around a press Site: who the client is, their
// Halo IDs, their tier, their storage entitlement.
//
// **This object is team-filtered and the others are not.** `HQ Tenant` carries
// a `team` field mirrored from its Site, and `press.api.client.get_list`
// filters any doctype that has one — for every caller, including system users
// (`client.py:422` reduces to `meta.has_field("team")`). So this list only
// returns rows whose team matches the operator's. Until the fleet team is real
// and staff belong to it, expect this screen to look emptier than the fleet is.
import { toast } from 'vue-sonner';
import { confirmDialog, icon } from '../../utils/components';

const GB = 1024 ** 3;

function gb(bytes) {
	if (!bytes) return '0 GB';
	return `${(Number(bytes) / GB).toFixed(1)} GB`;
}

export default {
	doctype: 'HQ Tenant',
	whitelistedMethods: {
		provisionStorage: 'provision_storage',
		syncTierToHalo: 'sync_tier_to_halo',
		syncStorageToHalo: 'sync_storage_to_halo',
		moveToTier: 'move_to_tier',
	},
	list: {
		route: '/hq/tenants',
		title: 'Tenants',
		orderBy: 'customer_name asc',
		fields: [
			'site',
			'customer_name',
			'status',
			'tier',
			'seats',
			'storage_mode',
			'storage_ceiling_gb',
			'storage_bytes_measured',
			'halo_client_id',
		],
		filterControls() {
			return [
				{
					type: 'select',
					fieldname: 'tier',
					options: ['', 'Basecamp', 'Trail', 'ERP', 'Summit'],
					default: '',
					placeholder: 'Tier',
					condition: true,
				},
				{
					type: 'select',
					fieldname: 'status',
					options: ['', 'Active', 'Suspended'],
					default: '',
					placeholder: 'Status',
					condition: true,
				},
				{
					type: 'select',
					fieldname: 'storage_mode',
					options: ['', 'None', 'BYO', 'ETG Commissioned'],
					default: '',
					placeholder: 'Storage',
					condition: true,
				},
			];
		},
		columns: [
			{ label: 'Customer', fieldname: 'customer_name', width: '220px' },
			{ label: 'Site', fieldname: 'site', class: 'max-w-sm' },
			{ label: 'Tier', fieldname: 'tier', width: '110px' },
			{
				label: 'Status',
				fieldname: 'status',
				width: '110px',
				type: 'Badge',
				theme: (value) => (value === 'Active' ? 'green' : 'red'),
			},
			{ label: 'Seats', fieldname: 'seats', width: '80px', align: 'right' },
			{
				label: 'Storage',
				fieldname: 'storage_bytes_measured',
				width: '150px',
				align: 'right',
				// Used against entitlement, because either number alone is
				// meaningless — 300 GB is fine or over depending on the ceiling.
				format: (value, row) =>
					row.storage_mode === 'ETG Commissioned'
						? `${gb(value)} / ${row.storage_ceiling_gb || 0} GB`
						: '—',
			},
		],
	},
	detail: {
		titleField: 'customer_name',
		route: '/hq/tenants/:name',
		statusBadge({ documentResource: tenant }) {
			return {
				label: tenant.doc.status,
				theme: tenant.doc.status === 'Active' ? 'green' : 'red',
			};
		},
		breadcrumbs({ documentResource: tenant }) {
			return [
				{ label: 'Tenants', route: '/hq/tenants' },
				{
					label: tenant.doc.customer_name || tenant.doc.name,
					route: `/hq/tenants/${tenant.doc.name}`,
				},
			];
		},
		actions({ documentResource: tenant }) {
			const done = (message) => ({
				onSuccess: () => {
					toast.success(message);
					tenant.reload();
				},
			});

			return [
				{
					label: 'Open site',
					variant: 'solid',
					condition: () => !!tenant.doc.site,
					onClick: () => window.open(`/dashboard/sites/${tenant.doc.site}`, '_blank'),
				},
				{
					label: 'Storage',
					button: { label: 'Storage', slots: { icon: icon('hard-drive') } },
					condition: () => tenant.doc.storage_mode === 'ETG Commissioned',
					options: [
						{
							label: 'Provision storage',
							icon: icon('hard-drive'),
							onClick() {
								confirmDialog({
									title: 'Provision storage',
									message:
										'Create or repair the commissioned bucket and its scoped key. Safe to run again — it repairs rather than duplicates.',
									onSuccess: ({ hide }) =>
										tenant.provisionStorage.submit(null, {
											onSuccess: (result) => {
												const out = result || {};
												toast.success(
													`Bucket ${out.bucket} ready — retention ${out.retention_days} days, replication ${out.replication ? 'configured' : 'pending'}`,
												);
												hide();
												tenant.reload();
											},
										}),
								});
							},
						},
						{
							label: 'Sync storage billing to Halo',
							icon: icon('dollar-sign'),
							onClick: () => tenant.syncStorageToHalo.submit(null, done('Storage line updated')),
						},
					],
				},
				{
					label: 'Billing',
					button: { label: 'Billing', slots: { icon: icon('dollar-sign') } },
					options: [
						{
							label: 'Sync tier and seats to Halo',
							icon: icon('refresh-cw'),
							onClick: () => tenant.syncTierToHalo.submit(null, done('Tier line updated')),
						},
						{
							label: 'View in Desk',
							icon: icon('external-link'),
							onClick: () => window.open(`/app/hq-tenant/${tenant.doc.name}`, '_blank'),
						},
					],
				},
			];
		},
		tabs: [
			{
				label: 'Overview',
				icon: icon('home'),
				route: 'overview',
				type: 'Component',
				component: () => import('../../pages/hq/RecordOverview.vue'),
				props: (tenant) => ({
					doc: tenant.doc,
					sections: [
						{
							label: 'Commercial',
							fields: [
								{ label: 'Tier', fieldname: 'tier' },
								{ label: 'Licensed seats', fieldname: 'seats' },
								{ label: 'Halo client', fieldname: 'halo_client_id' },
								{ label: 'Halo tier line', fieldname: 'halo_software_licence_id' },
								{ label: 'Halo storage line', fieldname: 'halo_storage_licence_id' },
							],
						},
						{
							label: 'Storage entitlement',
							description:
								'The ceiling is derived from seats and blocks. To give a client more room, sell a block.',
							condition: (doc) => doc.storage_mode === 'ETG Commissioned',
							fields: [
								{ label: 'Ceiling', fieldname: 'storage_ceiling_gb', format: (v) => `${v} GB` },
								{ label: 'Purchased blocks', fieldname: 'storage_purchased_blocks' },
								{ label: 'Auto-granted blocks', fieldname: 'storage_auto_blocks' },
								{ label: 'Measured', fieldname: 'storage_bytes_measured', format: gb },
								{
									// Deleted by the client, still held by the bucket, still
									// billed. Shown because the site cannot see it.
									label: 'Retained (deleted, still billed)',
									fieldname: 'storage_retained_bytes',
									format: gb,
								},
								{ label: 'Measured at', fieldname: 'storage_measured_at' },
							],
						},
						{
							label: 'Storage provisioning',
							condition: (doc) => doc.storage_mode === 'ETG Commissioned',
							fields: [
								{ label: 'State', fieldname: 'storage_provision_state' },
								{ label: 'Bucket', fieldname: 'storage_bucket' },
								{ label: 'Region', fieldname: 'storage_region' },
								{ label: 'Provisioned at', fieldname: 'storage_provisioned_at' },
								{ label: 'Last error', fieldname: 'storage_provision_error' },
							],
						},
						{
							label: 'Press',
							fields: [
								{ label: 'Site', fieldname: 'site' },
								{ label: 'Team', fieldname: 'team' },
								{ label: 'Token issued', fieldname: 'token_issued_at' },
							],
						},
					],
				}),
			},
		],
	},
};
