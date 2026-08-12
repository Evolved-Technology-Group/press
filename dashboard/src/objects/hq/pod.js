// Yukon HQ — pods.
//
// A pod is one app+database server pair shared by the clients of a tier. The
// lifecycle is Provision servers → Build servers → Attach benches → Finalize,
// and the third step is the one that is easy to miss and fails latest: press
// will place sites on a finalized server, then need a bench for the site's
// release group and find none. `POD-NO-BENCH` catches that hourly, but the
// button is here so it never gets that far.
//
// No `team` field on the doctype, so press's team filter does not apply.
import { toast } from 'vue-sonner';
import { confirmDialog, icon } from '../../utils/components';

export default {
	doctype: 'HQ Pod',
	whitelistedMethods: {
		provisionServers: 'provision_servers',
		buildServers: 'build_servers',
		attachBenches: 'attach_benches',
		finalize: 'finalize',
		grow: 'grow',
		tuneDatabaseMemory: 'tune_database_memory',
		repairStalledSetup: 'repair_stalled_setup',
		grantUsagePermission: 'grant_usage_permission',
		fixDigitalOceanProject: 'fix_digitalocean_project',
		closeToNewSites: 'close_to_new_sites',
		openToNewSites: 'open_to_new_sites',
	},
	list: {
		route: '/hq/pods',
		title: 'Pods',
		orderBy: 'pool asc, label asc',
		fields: ['label', 'pool', 'status', 'app_server', 'database_server', 'site_count'],
		filterControls() {
			return [
				{
					type: 'select',
					fieldname: 'pool',
					options: ['', 'Basecamp', 'Trail', 'Demo', 'ERP'],
					default: '',
					placeholder: 'Tier',
					condition: true,
				},
				{
					type: 'select',
					fieldname: 'status',
					options: ['', 'Building', 'Filling', 'Full', 'Retired'],
					default: '',
					placeholder: 'Status',
					condition: true,
				},
			];
		},
		columns: [
			{ label: 'Pod', fieldname: 'label', width: '160px' },
			{ label: 'Tier', fieldname: 'pool', width: '120px' },
			{
				label: 'Status',
				fieldname: 'status',
				width: '120px',
				type: 'Badge',
				theme: (value) =>
					({ Filling: 'green', Full: 'orange', Building: 'blue', Retired: 'gray' })[
						value
					] || 'gray',
			},
			{ label: 'Sites', fieldname: 'site_count', width: '90px', align: 'right' },
			{ label: 'App server', fieldname: 'app_server', class: 'max-w-sm' },
			{ label: 'Database server', fieldname: 'database_server', class: 'max-w-sm' },
		],
	},
	detail: {
		titleField: 'label',
		route: '/hq/pods/:name',
		statusBadge({ documentResource: pod }) {
			return {
				label: pod.doc.status,
				theme:
					{ Filling: 'green', Full: 'orange', Building: 'blue', Retired: 'gray' }[
						pod.doc.status
					] || 'gray',
			};
		},
		breadcrumbs({ documentResource: pod }) {
			return [
				{ label: 'Pods', route: '/hq/pods' },
				{ label: pod.doc.label || pod.doc.name, route: `/hq/pods/${pod.doc.name}` },
			];
		},
		actions({ documentResource: pod }) {
			const done = (message) => ({
				onSuccess: () => {
					toast.success(message);
					pod.reload();
				},
			});

			return [
				{
					label: 'Attach benches',
					variant: 'solid',
					// Deliberately promoted rather than buried in Options: it is the
					// step between a built server and a usable one, and the one an
					// operator is most likely not to know exists.
					condition: () => !!pod.doc.app_server && pod.doc.status !== 'Retired',
					onClick() {
						confirmDialog({
							title: 'Attach benches',
							message: `Deploy a bench onto ${pod.doc.app_server} for every image this tier can serve? Reuses the existing build where one exists.`,
							onSuccess: ({ hide }) =>
								pod.attachBenches.submit(null, {
									onSuccess: (result) => {
										const out = result || {};
										const parts = [];
										if (out.attached?.length)
											parts.push(`deploying ${out.attached.join(', ')}`);
										if (out.already_attached?.length)
											parts.push(`already attached: ${out.already_attached.join(', ')}`);
										if (out.failed?.length)
											parts.push(`failed: ${out.failed.join('; ')}`);
										toast.success(parts.join(' — ') || 'Nothing to attach');
										hide();
										pod.reload();
									},
								}),
						});
					},
				},
				{
					label: 'Lifecycle',
					button: { label: 'Lifecycle', slots: { icon: icon('more-horizontal') } },
					options: [
						{
							label: 'Provision servers',
							icon: icon('plus-circle'),
							condition: () => !pod.doc.app_server,
							onClick() {
								confirmDialog({
									title: 'Provision servers',
									message: `Create a ${pod.doc.pool} pair for ${pod.doc.label}? This starts billing on two droplets.`,
									onSuccess: ({ hide }) =>
										pod.provisionServers.submit(null, {
											...done('Servers requested'),
											onSuccess: () => {
												toast.success('Servers requested');
												hide();
												pod.reload();
											},
										}),
								});
							},
						},
						{
							label: 'Build servers',
							icon: icon('tool'),
							condition: () => !!pod.doc.app_server,
							onClick: () =>
								pod.buildServers.submit(null, done('Base build queued — around 40 minutes')),
						},
						{
							label: 'Finalize',
							icon: icon('check-circle'),
							condition: () => !!pod.doc.app_server && pod.doc.status !== 'Filling',
							onClick() {
								confirmDialog({
									title: 'Finalize pod',
									message: `Verify the agent and MariaDB over SSH first. Open ${pod.doc.label} to new sites?`,
									onSuccess: ({ hide }) =>
										pod.finalize.submit(null, {
											onSuccess: () => {
												toast.success('Pod is open to new sites');
												hide();
												pod.reload();
											},
										}),
								});
							},
						},
						{
							label: 'Repair stalled setup',
							icon: icon('life-buoy'),
							onClick: () => pod.repairStalledSetup.submit(null, done('Repair attempted')),
						},
						{
							label: 'Fix DigitalOcean project',
							icon: icon('folder'),
							onClick: () =>
								pod.fixDigitalOceanProject.submit(null, done('Droplet placement checked')),
						},
					],
				},
				{
					label: 'Capacity',
					button: { label: 'Capacity', slots: { icon: icon('trending-up') } },
					options: [
						{
							label: 'Grow (CPU and RAM)',
							icon: icon('trending-up'),
							onClick() {
								confirmDialog({
									title: 'Grow pod',
									message:
										'Resize both halves to the stage this pod needs. CPU and RAM only — reversible.',
									onSuccess: ({ hide }) =>
										pod.grow.submit(
											{ with_disk: false },
											{
												onSuccess: () => {
													toast.success('Resize requested');
													hide();
													pod.reload();
												},
											},
										),
								});
							},
						},
						{
							label: 'Grow including disk (irreversible)',
							icon: icon('alert-triangle'),
							onClick() {
								confirmDialog({
									title: 'Grow pod including disk',
									message:
										'DigitalOcean cannot shrink a disk. This permanently raises this pod’s cost floor. Only do this for a disk alert.',
									onSuccess: ({ hide }) =>
										pod.grow.submit(
											{ with_disk: true },
											{
												onSuccess: () => {
													toast.success('Resize requested');
													hide();
													pod.reload();
												},
											},
										),
								});
							},
						},
						{
							label: 'Tune database memory',
							icon: icon('sliders'),
							onClick: () => pod.tuneDatabaseMemory.submit(null, done('Database tuned')),
						},
						{
							label: 'Grant usage permission',
							icon: icon('bar-chart-2'),
							onClick: () =>
								pod.grantUsagePermission.submit(
									null,
									done('Usage permission granted — metering reports within the hour'),
								),
						},
					],
				},
				{
					label: 'Placement',
					button: { label: 'Placement', slots: { icon: icon('git-pull-request') } },
					options: [
						{
							label: 'Close to new sites',
							icon: icon('lock'),
							condition: () => pod.doc.status === 'Filling',
							onClick: () => pod.closeToNewSites.submit(null, done('Closed to new sites')),
						},
						{
							label: 'Reopen to new sites',
							icon: icon('unlock'),
							condition: () => pod.doc.status === 'Full',
							onClick: () => pod.openToNewSites.submit(null, done('Open to new sites')),
						},
						{
							label: 'View in Desk',
							icon: icon('external-link'),
							onClick: () => window.open(`/app/hq-pod/${pod.doc.name}`, '_blank'),
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
				props: (pod) => ({
					doc: pod.doc,
					sections: [
						{
							label: 'Placement',
							fields: [
								{ label: 'Tier', fieldname: 'pool' },
								{ label: 'Status', fieldname: 'status' },
								{ label: 'Sites', fieldname: 'site_count' },
							],
						},
						{
							label: 'Servers',
							description:
								'A site’s database lives on whichever database server its app server is paired with.',
							fields: [
								{ label: 'App server', fieldname: 'app_server' },
								{ label: 'Database server', fieldname: 'database_server' },
								{ label: 'App plan', fieldname: 'current_app_plan' },
								{ label: 'Database plan', fieldname: 'current_database_plan' },
							],
						},
					],
				}),
			},
		],
	},
};
