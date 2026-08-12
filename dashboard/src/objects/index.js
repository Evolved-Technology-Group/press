import site from './site';
import group from './group';
import bench from './bench';
import marketplace from './marketplace';
import server from './server';
import notification from './notification';
import accessRequests from './accessRequests';
// Yukon HQ. New files only, plus these entries — generateRoutes() does the rest.
import hqAlert from './hq/alert';
import hqOnboarding from './hq/onboarding';
import hqPod from './hq/pod';
import hqTenant from './hq/tenant';

let objects = {
	Site: site,
	Group: group,
	Bench: bench,
	Marketplace: marketplace,
	Server: server,
	Notification: notification,
	AccessRequests: accessRequests,
	HQFleetAlert: hqAlert,
	HQPod: hqPod,
	HQTenant: hqTenant,
	HQOnboarding: hqOnboarding,
};

export function getObject(name) {
	return objects[name];
}

export default objects;
