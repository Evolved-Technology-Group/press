// Yukon HQ — onboarding.
//
// Provisioning a client goes through here rather than through press's own New
// Site flow: press cannot tell tiers apart and would create the site with no
// plan at all, which means no caps and no alerts.
import { toast } from 'vue-sonner';
import { confirmDialog, icon } from '../../utils/components';

export default {
	doctype: 'HQ Onboarding',
	whitelistedMethods: {
		provision: 'provision',
	},
	list: {
		route: '/hq/onboarding',
		title: 'Onboarding',
		orderBy: 'creation desc',
		fields: ['customer_name', 'subdomain', 'tier', 'status', 'site', 'partner_slug', 'error'],
		filterControls() {
			return [
				{
					type: 'select',
					fieldname: 'status',
					options: ['', 'Draft', 'Provisioning', 'Complete', 'Failed'],
					default: '',
					placeholder: 'Status',
					condition: true,
				},
				{
					type: 'select',
					fieldname: 'tier',
					options: ['', 'Basecamp', 'Trail', 'ERP', 'Summit'],
					default: '',
					placeholder: 'Tier',
					condition: true,
				},
			];
		},
		columns: [
			{ label: 'Customer', fieldname: 'customer_name', width: '220px' },
			{ label: 'Subdomain', fieldname: 'subdomain', width: '180px' },
			{ label: 'Tier', fieldname: 'tier', width: '110px' },
			{
				label: 'Status',
				fieldname: 'status',
				width: '130px',
				type: 'Badge',
				theme: (value) =>
					({ Complete: 'green', Failed: 'red', Provisioning: 'blue', Draft: 'gray' })[
						value
					] || 'gray',
			},
			{ label: 'Site', fieldname: 'site', class: 'max-w-sm' },
			{
				label: 'Created',
				fieldname: 'creation',
				type: 'Timestamp',
				align: 'right',
				width: '160px',
			},
		],
	},
	detail: {
		titleField: 'customer_name',
		route: '/hq/onboarding/:name',
		statusBadge({ documentResource: onboarding }) {
			return {
				label: onboarding.doc.status,
				theme:
					{ Complete: 'green', Failed: 'red', Provisioning: 'blue', Draft: 'gray' }[
						onboarding.doc.status
					] || 'gray',
			};
		},
		breadcrumbs({ documentResource: onboarding }) {
			return [
				{ label: 'Onboarding', route: '/hq/onboarding' },
				{
					label: onboarding.doc.customer_name || onboarding.doc.name,
					route: `/hq/onboarding/${onboarding.doc.name}`,
				},
			];
		},
		actions({ documentResource: onboarding }) {
			return [
				{
					label: 'Provision',
					variant: 'solid',
					// Retryable on purpose: a failed run resumes past a site that
					// survived an earlier attempt rather than creating a second one.
					condition: () => onboarding.doc.status !== 'Complete',
					onClick() {
						confirmDialog({
							title: 'Provision client',
							message: `Create ${onboarding.doc.subdomain} on the filling ${onboarding.doc.tier} pod, with that tier's plan and apps?`,
							onSuccess: ({ hide }) =>
								onboarding.provision.submit(null, {
									onSuccess: (site) => {
										toast.success(`Provisioned ${site}`);
										hide();
										onboarding.reload();
									},
								}),
						});
					},
				},
				{
					label: 'Open site',
					condition: () => !!onboarding.doc.site,
					onClick: () =>
						window.open(`/dashboard/sites/${onboarding.doc.site}`, '_blank'),
				},
				{
					label: 'View in Desk',
					slots: { icon: icon('external-link') },
					onClick: () =>
						window.open(`/app/hq-onboarding/${onboarding.doc.name}`, '_blank'),
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
				props: (onboarding) => ({
					doc: onboarding.doc,
					sections: [
						{
							label: 'Client',
							fields: [
								{ label: 'Customer', fieldname: 'customer_name' },
								{ label: 'Subdomain', fieldname: 'subdomain' },
								{ label: 'Halo client', fieldname: 'halo_client_id' },
								{ label: 'Partner', fieldname: 'partner_slug' },
							],
						},
						{
							label: 'Placement',
							fields: [
								{ label: 'Tier', fieldname: 'tier' },
								{ label: 'App bundle', fieldname: 'app_bundle' },
								{ label: 'Pod', fieldname: 'pod' },
								{ label: 'Site', fieldname: 'site' },
								{ label: 'Tenant', fieldname: 'tenant' },
							],
						},
						{
							label: 'Result',
							condition: (doc) => doc.status === 'Failed',
							fields: [{ label: 'Error', fieldname: 'error' }],
						},
					],
				}),
			},
		],
	},
};
