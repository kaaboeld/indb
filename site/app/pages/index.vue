<script setup lang="ts">
import SectionHero from '~/components/sections/SectionHero.vue'
import SectionManifesto from '~/components/sections/SectionManifesto.vue'
import SectionPhilosophy from '~/components/sections/SectionPhilosophy.vue'
import SectionRoadmap from '~/components/sections/SectionRoadmap.vue'
import SectionBlind from '~/components/sections/SectionBlind.vue'
import SectionSpatial from '~/components/sections/SectionSpatial.vue'
import SectionModules from '~/components/sections/SectionModules.vue'
import SectionModularity from '~/components/sections/SectionModularity.vue'
import SectionConnectors from '~/components/sections/SectionConnectors.vue'
import SectionModelUplift from '~/components/sections/SectionModelUplift.vue'
import SectionPerformance from '~/components/sections/SectionPerformance.vue'
import SectionSignedMemory from '~/components/sections/SectionSignedMemory.vue'
import SectionProtocols from '~/components/sections/SectionProtocols.vue'
import SectionApi from '~/components/sections/SectionApi.vue'
import SectionRealityGuard from '~/components/sections/SectionRealityGuard.vue'
import SectionUseCases from '~/components/sections/SectionUseCases.vue'
import SectionCta from '~/components/sections/SectionCta.vue'
import SectionContact from '~/components/sections/SectionContact.vue'

usePresentationGsap()
</script>

<template>
  <main>
    <AppNav />
    <SectionHero />
    <SectionManifesto />
    <SectionPhilosophy />
    <SectionRoadmap />
    <SectionBlind />
    <SectionSpatial />
    <SectionModules />
    <SectionModularity />
    <SectionConnectors />
    <SectionModelUplift />
    <SectionPerformance />
    <SectionSignedMemory />
    <SectionProtocols />
    <SectionApi />
    <SectionRealityGuard />
    <SectionUseCases />
    <SectionCta />
    <SectionContact />
    <AppFooter />
  </main>
</template>
