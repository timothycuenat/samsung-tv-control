<script lang="ts">
  import { Power } from 'lucide-svelte';
  import { createEventDispatcher } from 'svelte';

  export let tvOn: boolean;
  export let loading: boolean;
  export let actionType: 'on' | 'off' | null = null; // 'on' si on allume, 'off' si on éteint
  export let disabled: boolean = false;

  const dispatch = createEventDispatcher();
  let hover = false;

  // Variables locales pour le style
  let powerClass = '';
  let powerStyle = '';
  let powerText = '';
  let powerIcon = '';

  $: {
    let border = '';
    let bg = '';
    let text = '';
    let iconColor = '';
    let style = '';
    let animate = '';

    if (loading) {
      if (actionType === 'on') {
        border = 'border-green-700 border';
        bg = '!bg-green-700 !text-white';
        text = 'Turning on';
        iconColor = '!text-white';
        style = 'background-color:#15803d;color:#fff;';
        animate = 'animate-pulse';
      } else {
        border = 'border-red-700 border';
        bg = '!bg-red-700 !text-white';
        text = 'Turning off';
        iconColor = '!text-white';
        style = 'background-color:#b91c1c;color:#fff;';
        animate = 'animate-pulse';
      }
    } else if (!tvOn && hover) {
      border = 'border-green-600 border';
      bg = 'bg-green-50 text-green-700';
      text = 'Turn on ?';
      iconColor = '!text-green-700';
      style = 'background-color:#f0fdf4;color:#15803d;';
      animate = 'cursor-pointer';
    } else if (!tvOn) {
      border = 'border-red-600 border';
      bg = 'bg-red-50 text-red-700';
      text = 'OFF';
      iconColor = '!text-red-700';
      style = 'background-color:#fef2f2;color:#b91c1c;';
      animate = 'cursor-pointer';
    } else if (tvOn && hover) {
      border = 'border-red-600 border';
      bg = 'bg-red-50 text-red-700';
      text = 'Turn off ?';
      iconColor = '!text-red-700';
      style = 'background-color:#fef2f2;color:#b91c1c;';
      animate = 'cursor-pointer';
    } else if (tvOn) {
      border = '!bg-green-600 !text-white';
      bg = '';
      text = 'ON';
      iconColor = '!text-white';
      style = 'background-color:#16a34a;color:#fff;';
      animate = 'cursor-pointer';
    }

    // Bordure transparente par défaut si aucune bordure colorée n'est définie
    if (!border.includes('border-')) {
      border = 'border border-transparent ' + border;
    }

    powerClass = `flex w-full items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ring-offset-background ${border} ${bg} shadow ${animate}`;
    powerStyle = style;
    powerText = text;
    powerIcon = iconColor;
  }
</script>

<button
  type="button"
  {disabled}
  aria-disabled={disabled}
  on:mouseenter={() => hover = true}
  on:mouseleave={() => hover = false}
  class={powerClass}
  style={powerStyle}
  on:click={() => !disabled && dispatch('toggle')}
>
  <Power class={`w-4 h-4 ${powerIcon}`} />
  <span class={`font-semibold ${loading ? '!text-white' : ''}`}>{powerText}</span>
</button> 