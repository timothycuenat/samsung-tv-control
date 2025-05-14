<script lang="ts">
  import { Trash2 } from 'lucide-svelte';
  import { createEventDispatcher } from 'svelte';

  export let loading: boolean = false;
  export let disabled: boolean = false;

  const dispatch = createEventDispatcher();
  let hover = false;

  // Variables locales pour le style
  let buttonClass = '';
  let buttonStyle = '';
  let buttonText = '';
  let iconColor = '';

  $: {
    let border = '';
    let bg = '';
    let text = '';
    let style = '';
    let animate = '';

    if (loading) {
      border = 'border-destructive border';
      bg = 'bg-destructive text-destructive-foreground';
      text = 'Deleting...';
      iconColor = 'text-destructive-foreground';
      style = '';
      animate = 'animate-pulse';
    } else {
      border = 'border-destructive border';
      bg = 'bg-destructive text-destructive-foreground hover:bg-destructive/90';
      text = 'Delete all images';
      iconColor = 'text-destructive-foreground';
      style = '';
      animate = 'cursor-pointer';
    }

    buttonClass = `flex w-full items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background ${border} ${bg} shadow ${animate}`;
    buttonStyle = style;
    buttonText = text;
  }
</script>

<button
  type="button"
  {disabled}
  aria-disabled={disabled}
  on:mouseenter={() => hover = true}
  on:mouseleave={() => hover = false}
  class={buttonClass}
  style={buttonStyle}
  on:click={() => !disabled && dispatch('click')}
>
  <Trash2 class={`w-4 h-4 ${iconColor}`} />
  <span class="font-semibold">{buttonText}</span>
</button> 