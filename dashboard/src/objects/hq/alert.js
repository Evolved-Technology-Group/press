// Yukon HQ — fleet alerts.
//
// The queue a tech opens first. Critical alerts are also delivered by email and
// Telegram (`yukon_hq.alerting`), so this list is the record and the working
// surface rather than the only way anyone finds out.
//
// `HQ Fleet Alert` carries no `team` field, so press's team filter in
// `press.api.client.get_list` does not apply and a desk user sees the whole
// fleet — which is the point of the screen.
import { icon } from '../../utils/components';
import { toast } from 'vue-sonner';

export default {
	doctype: 'HQ Fleet Alert',
	whitelistedMethods: {
		resolve: 'resolve',
	},
	list: {
		route: '/hq/alerts',
		title: 'Fleet Alerts',
		// Open first, then newest: an operator wants what is wrong now, and the
		// resolved history only when they go looking for it.
		orderBy: 'status asc, raised_on desc',
		fields: ['alert_type', 'severity', 'status', 'subject', 'pod', 'site', 'detail'],
		filterControls() {
			return [
				{
					type: 'tab',
					fieldname: 'status',
					options: ['Open', 'Resolved'],
					default: 'Open',
					condition: true,
				},
				{
					type: 'select',
					fieldname: 'severity',
					options: ['', 'Critical', 'Warning'],
					default: '',
					placeholder: 'Severity',
					condition: true,
				},
			];
		},
		columns: [
			{
				label: 'Severity',
				fieldname: 'severity',
				width: '110px',
				type: 'Badge',
				theme: (value) => ({ Critical: 'red', Warning: 'orange' })[value] || 'gray',
			},
			{ label: 'Type', fieldname: 'alert_type', width: '210px' },
			{ label: 'Subject', fieldname: 'subject', width: '220px' },
			{ label: 'Detail', fieldname: 'detail', class: 'max-w-xl' },
			{
				label: 'Raised',
				fieldname: 'raised_on',
				type: 'Timestamp',
				align: 'right',
				width: '170px',
			},
		],
	},
	detail: {
		titleField: 'alert_type',
		route: '/hq/alerts/:name',
		statusBadge({ documentResource: alert }) {
			return {
				label: alert.doc.status,
				theme: alert.doc.status === 'Open' ? 'orange' : 'green',
			};
		},
		breadcrumbs({ documentResource: alert }) {
			return [
				{ label: 'Fleet Alerts', route: '/hq/alerts' },
				{ label: alert.doc.alert_type, route: `/hq/alerts/${alert.doc.name}` },
			];
		},
		actions({ documentResource: alert }) {
			return [
				{
					label: 'Resolve',
					variant: 'solid',
					condition: () => alert.doc.status === 'Open',
					onClick() {
						// Resolving by hand does not fix the condition. The hourly
						// sweep re-raises anything still true, which is exactly the
						// behaviour that keeps this list honest.
						return alert.resolve.submit(null, {
							onSuccess: () => toast.success('Alert resolved'),
						});
					},
				},
				{
					label: 'View in Desk',
					slots: { icon: icon('external-link') },
					onClick() {
						window.open(`/app/hq-fleet-alert/${alert.doc.name}`, '_blank');
					},
				},
			];
		},
		tabs: [
			{
				label: 'Detail',
				icon: icon('alert-triangle'),
				route: 'detail',
				type: 'Component',
				component: () => import('../../pages/hq/RecordOverview.vue'),
				props: (alert) => ({
					doc: alert.doc,
					sections: [
						{
							label: 'Condition',
							fields: [
								{ label: 'Type', fieldname: 'alert_type' },
								{ label: 'Severity', fieldname: 'severity' },
								{ label: 'Status', fieldname: 'status' },
								{ label: 'Subject', fieldname: 'subject' },
								{ label: 'Pod', fieldname: 'pod' },
								{ label: 'Site', fieldname: 'site' },
							],
						},
						{
							label: 'What happened',
							fields: [{ label: 'Detail', fieldname: 'detail' }],
						},
						{
							label: 'Timing',
							fields: [
								{ label: 'Raised', fieldname: 'raised_on' },
								{ label: 'Resolved', fieldname: 'resolved_on' },
							],
						},
					],
				}),
			},
		],
	},
};
