<script lang="ts" module>
	import type { HTMLAttributes } from "svelte/elements";
	// Définir le type WithElementRef pour remplacer l'importation manquante
	type WithElementRef<T, U extends HTMLElement = HTMLElement> = T & { ref?: U | null };

	export type CardEvents = {
		click: MouseEvent;
	};
</script>

<script lang="ts">
	import { cn } from "$lib/utils.js";

	let {
		ref = $bindable(null),
		class: className,
		children,
		...restProps
	}: WithElementRef<HTMLAttributes<HTMLDivElement>> = $props();
</script>

<div
	bind:this={ref}
	class={cn("bg-card text-card-foreground rounded-lg border shadow-sm", className)}
	{...restProps}
	on:click
>
	{@render children?.()}
</div>
