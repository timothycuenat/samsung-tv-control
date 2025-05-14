<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import Card from '$lib/components/ui/card/card.svelte';
  import Button from '$lib/components/ui/button/button.svelte';
  import Alert from '$lib/components/ui/alert/alert.svelte';
  import { tvService } from '$lib/services/tvService';
  import type { TVStatus } from '$lib/services/tvService';
  import { Tv, LoaderCircle, ArrowLeft, Power, PowerOff, Image as ArtIcon, BadgeCheck, BadgeX, Monitor } from 'lucide-svelte';
  import { get } from 'svelte/store';
  import Toggle from '$lib/components/ui/toggle/toggle.svelte';
  import PowerToggle from '$lib/components/PowerToggle.svelte';
  import ArtModeToggle from '$lib/components/ArtModeToggle.svelte';

  let ip = '';
  let tv: TVStatus | null = null;
  let loading = true;
  let error = '';
  let actionLoading = false;
  let actionError = '';
  let powerPressed = false;
  let artModePressed = false;
  let powerLoading = false;
  let artModeLoading = false;
  let powerHover = false;
  let powerActionType: 'on' | 'off' | null = null;
  let artModeActionType: 'on' | 'off' | null = null;
  $: if (tv) {
    powerPressed = tv.tv_on;
    artModePressed = tv.art_mode;
  }
  let prevPower = powerPressed;
  let prevArt = artModePressed;
  $: if (tv && powerPressed !== prevPower) {
    prevPower = powerPressed;
    if (powerPressed !== tv.tv_on) togglePower();
  }
  $: if (tv && artModePressed !== prevArt) {
    prevArt = artModePressed;
    if (artModePressed !== tv.art_mode) toggleArtMode();
  }

  onMount(async () => {
    ip = get(page).params.ip;
    await fetchTV();
  });

  async function fetchTV() {
    loading = true;
    error = '';
    try {
      tv = await tvService.getTVStatus(ip);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Erreur inconnue';
    } finally {
      loading = false;
    }
  }

  async function togglePower() {
    if (!tv) return;
    powerActionType = tv.tv_on ? 'off' : 'on';
    powerLoading = true;
    actionError = '';
    try {
      await tvService.powerControl(ip, tv.tv_on ? 'off' : 'on');
      await fetchTV();
    } catch (e) {
      actionError = e instanceof Error ? e.message : 'Erreur action power';
    } finally {
      powerLoading = false;
      powerActionType = null;
    }
  }

  async function toggleArtMode() {
    if (!tv) return;
    artModeActionType = tv.art_mode ? 'off' : 'on';
    artModeLoading = true;
    actionError = '';
    try {
      await tvService.artMode(ip, tv.art_mode ? 'off' : 'on');
      await fetchTV();
    } catch (e) {
      actionError = e instanceof Error ? e.message : 'Erreur action art mode';
    } finally {
      artModeLoading = false;
      artModeActionType = null;
    }
  }

  function goBack() {
    goto('/');
  }
</script>

<div class="min-h-screen bg-gray-50 flex flex-col items-center py-8 px-4 sm:py-12 sm:px-0">
  <div class="w-full max-w-xl">
    <Button variant="ghost" size="sm" class="mb-3 sm:mb-4 flex items-center gap-2" on:click={goBack}>
      <ArrowLeft class="w-4 h-4" /> Retour
    </Button>
    <Card class="p-4 sm:p-8 bg-white shadow-md rounded-xl">
      {#if loading}
        <div class="flex justify-center my-6 sm:my-8"><LoaderCircle class="animate-spin w-6 h-6 sm:w-8 sm:h-8 text-gray-400" /></div>
      {:else if error}
        <Alert variant="destructive" class="mb-4">{error}</Alert>
      {:else if tv}
        <div class="flex items-center gap-3 sm:gap-4 mb-4 sm:mb-6">
          <Tv class="w-10 h-10 sm:w-14 sm:h-14 text-gray-400" />
          <div>
            <div class="text-lg sm:text-2xl font-bold">{tv.raw_device_info.device.name}</div>
            <div class="text-gray-500 text-xs sm:text-sm">{tv.raw_device_info.device.modelName} · {tv.raw_device_info.device.ip}</div>
          </div>
        </div>
        <div class="flex flex-col gap-3 sm:gap-4">
          <div class="w-full">
            <PowerToggle
              tvOn={!!tv?.tv_on}
              loading={powerLoading}
              actionType={powerActionType}
              disabled={powerLoading || artModeLoading}
              on:toggle={togglePower}
            />
          </div>
          <div class="w-full">
            <ArtModeToggle
              artOn={!!tv?.art_mode}
              loading={artModeLoading}
              actionType={artModeActionType}
              disabled={powerLoading || artModeLoading}
              on:toggle={toggleArtMode}
            />
          </div>
        </div>
        
        {#if actionError}
          <Alert variant="destructive" class="mt-4">{actionError}</Alert>
        {/if}
      {/if}
    </Card>
  </div>
</div>

<style>
  .animate-spin {
    animation: spin 1s linear infinite;
  }
  @keyframes spin {
    100% { transform: rotate(360deg); }
  }
</style> 