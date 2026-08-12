<!--
  One overview for every Yukon HQ record.

  Four objects needed the same thing — grouped, read-only facts about a document
  the actions above already know how to change — so this takes the sections as a
  prop instead of existing four times with different labels. Anything genuinely
  bespoke belongs in its own component rather than as another branch in here.
-->
<template>
	<div class="space-y-6 p-5">
		<div v-for="section in visibleSections" :key="section.label">
			<h3 class="text-base font-medium text-ink-gray-9">{{ section.label }}</h3>
			<p v-if="section.description" class="mt-1 text-p-sm text-ink-gray-6">
				{{ section.description }}
			</p>
			<div class="mt-3 grid grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-2">
				<div
					v-for="field in visibleFields(section)"
					:key="field.fieldname"
					class="flex items-baseline justify-between gap-4 border-b border-outline-gray-1 pb-2"
				>
					<span class="text-p-sm text-ink-gray-6">{{ field.label }}</span>
					<span class="text-right text-p-sm text-ink-gray-9">
						{{ display(field) }}
					</span>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
	doc: { type: Object, required: true },
	sections: { type: Array, required: true },
});

const visibleSections = computed(() =>
	props.sections.filter(
		(section) => !section.condition || section.condition(props.doc),
	),
);

function visibleFields(section) {
	return section.fields.filter(
		(field) => !field.condition || field.condition(props.doc),
	);
}

/**
 * Empty renders as an em dash rather than as nothing.
 *
 * A blank cell and a zero look identical at a glance, and on this screen the
 * difference is "never measured" versus "measured, and it is zero" — which for
 * storage and seats is the difference between a bug and a fact.
 */
function display(field) {
	const value = props.doc?.[field.fieldname];
	if (value === undefined || value === null || value === '') return '—';
	return field.format ? field.format(value, props.doc) : value;
}
</script>
