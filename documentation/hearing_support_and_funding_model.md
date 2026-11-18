# Health and Wellbeing Support, Access and Individual Outcomes

**Project:** Health and Wellbeing Population Simulator
**Document status:** Initial research specification — draft
**Scope:** General health and wellbeing support, service access, funding and individual outcomes

## 1. Core research principle

The simulator must not equate access to, receipt of, or engagement with a service or intervention with successful health and wellbeing outcomes.

Success must be considered in relation to whether individuals can access appropriate support, whether that support is suitable for their circumstances and preferences, and whether it produces meaningful outcomes that matter to them.

Receiving a service or obtaining a support resource is an intermediate event, not proof of benefit.

The simulator must not assume that:
- Identifying a need means an individual will seek help.
- Seeking help means appropriate services are accessible.
- Eligibility for funding means support is affordable or available.
- Receiving a service means the support is suitable.
- Starting or continuing an intervention means the individual benefits from it.
- More frequent or intensive use necessarily produces better outcomes.
- A more expensive or advanced intervention necessarily produces better outcomes.
- People who decline, discontinue or do not use a service have failed or are non-compliant.
- One type of support is appropriate for everyone with a similar identified need.

## 2. Separate dimensions of support and care

The simulation should represent the following dimensions independently. Their relevance and specific variables will depend on the type of need, service or intervention being modelled.

### 2.1 Need, recognition and help-seeking

Represent separately:
- A person's reported or observed needs.
- Whether a need has been assessed or formally established.
- Whether the person recognises or perceives a need.
- Whether the person wants support.
- Help-seeking intention.
- Actions taken to seek assistance.
- Reasons for seeking, delaying or declining support.

A reported difficulty must not automatically be treated as a clinical diagnosis. Unknown, unassessed and declined information must remain distinguishable.

### 2.2 Access to services and support

Whether an individual can access appropriate services or resources.

Variables may include:
- Geographic availability of providers.
- Travel distance and time.
- Waiting time.
- Service capacity.
- Availability of suitably qualified professionals.
- Communication and other accessibility requirements.
- Appointment availability.
- Digital access and service delivery options.
- Public, private or community service pathways.
- Awareness of available services.

### 2.3 Eligibility and funding

Whether an individual qualifies for available financial or other support.

Variables may include:
- Funding pathway.
- Eligibility status and criteria.
- Evidence required to establish eligibility.
- Government or other subsidy.
- Insurance contribution.
- Personal financial contribution.
- Funding restrictions and service limits.
- Policy version and effective date.

Eligibility must remain separate from access and affordability. A person may qualify for support but still be unable to obtain it.

### 2.4 Affordability

Whether the individual can afford recommended services, interventions and ongoing expenses.

Variables may include:
- Household financial resources.
- Service or intervention cost.
- Out-of-pocket contribution.
- Assessment and follow-up expenses.
- Travel and accommodation expenses.
- Maintenance and ongoing costs.
- Replacement or renewal costs.
- Financial hardship.

Eligibility and affordability must remain separate. A subsidy does not necessarily remove all financial barriers.

### 2.5 Suitability of support

Whether recommended support is appropriate for the individual's circumstances.

Consider:
- Identified needs and relevant assessment findings.
- Personal goals and preferences.
- Existing capabilities and support.
- Living, working and social circumstances.
- Accessibility and usability requirements.
- Cultural and communication considerations.
- Practical constraints.
- Risks, limitations and potential burdens.
- Alternative or complementary support options.

A diagnosis, demographic category or risk classification must not automatically determine which intervention is appropriate. Suitability depends on the individual and the type of support being considered.

### 2.6 Decision and commencement

Whether the individual decides to proceed with recommended support and whether it is actually provided.

Record separately:
- Recommended service or intervention.
- Support accepted, declined or deferred.
- Reason for the decision, where known.
- Referral and booking status.
- Service commencement or resource acquisition.
- Intervention type and provider.
- Commencement date.
- Initial adjustment or implementation.
- Follow-up availability.

A recommendation, referral, purchase or booking must not be treated as confirmation that support was received.

### 2.7 Engagement and continued use

Whether and how the individual chooses or is able to engage with the support.

Variables may include:
- Attendance and participation.
- Frequency and duration of engagement.
- Contexts in which support is used.
- Accessibility and usability.
- Perceived value and burden.
- Practical barriers.
- Reasons for reduced engagement.
- Reasons for discontinuation.
- Changes in preference or circumstances.

Non-use, missed appointments or discontinuation must not automatically be classified as failure or non-compliance. The reasons and circumstances should be represented where evidence is available.

### 2.8 Effectiveness and individual benefit

Whether the support produces meaningful benefits for the individual.

Potential outcomes depend on the domain and may include:
- Changes in relevant functional abilities.
- Symptom or difficulty changes.
- Physical and psychological functioning.
- Communication and participation.
- Confidence and independence.
- Daily activity and quality of life.
- Social connection and participation.
- Progress towards individual goals.
- Adverse effects or unintended consequences.

Effectiveness must be evaluated independently of service receipt, intervention ownership and engagement.

A measured change must not automatically be attributed to an intervention without considering other relevant influences and the strength of the evidence.

### 2.9 Satisfaction and longer-term outcomes

Record separately:
- Satisfaction with services and providers.
- Satisfaction with the support received.
- Perceived value and burden.
- Individual goal achievement.
- Continued benefit or changing needs.
- Longer-term functioning and wellbeing.
- Participation and independence.
- Ongoing access to support.
- Changes in support requirements.
- Continued engagement or discontinuation.

Objective measures, observed events and subjective experiences must remain distinguishable.

## 3. Types of support and intervention

The simulator should be capable of representing different forms of support, depending on the domain being studied.

Examples include:
- Assessment and monitoring.
- Preventive services.
- Clinical treatment.
- Rehabilitation and therapy.
- Medicines and other therapeutic interventions.
- Assistive and communication technology.
- Education and information.
- Counselling and psychosocial support.
- Community-based services.
- Social and practical support.
- Environmental modifications.
- Digital and remote services.
- Combined support approaches.
- No additional intervention, where appropriate to individual preferences and circumstances.

These options are not interchangeable. Suitability depends on individual circumstances, the nature of the need and relevant professional assessment.

The model must allow for multiple concurrent or sequential forms of support.

## 4. Public, private and other funding pathways

The simulator should represent funding arrangements appropriate to the country, population and service being modelled.

### Public pathways
Examples may include:
- Government-funded services.
- Subsidised treatment or support programs.
- Public hospitals and community health services.
- Disability and aged-care support arrangements.
- Veteran-specific support.
- Other applicable public assistance.

### Private pathways
Examples may include:
- Private providers.
- Private health insurance contributions.
- Self-funded services and interventions.
- Out-of-pocket expenses.
- Privately funded upgrades or additional services.

### Community and mixed pathways

Individuals may receive support through community organisations, charitable programs, family or informal networks, or combinations of public and private services.

Eligibility, availability, affordability, referral, service receipt and ongoing support must remain separate variables.

Policy arrangements must be versioned and linked to their effective dates. Country-specific rules must be configured and supported by appropriate evidence rather than assumed to apply universally.

## 5. Service characteristics and cost

Services and interventions may differ in complexity, intensity, duration, delivery method and cost.

The model should distinguish:
- Service or intervention type.
- Provider and workforce requirements.
- Technical or professional characteristics.
- Service intensity and duration.
- Delivery setting and method.
- Availability and capacity.
- Direct cost.
- Funding contribution.
- Out-of-pocket expense.
- Ongoing resource requirements.
- Individual suitability.

Cost, complexity or intensity must not independently determine effectiveness or individual benefit.

## 6. Individual outcome measurement

The simulator must preserve the distinction between:

1. Need recognition and help-seeking.
2. Access to appropriate services and support.
3. Eligibility and funding.
4. Affordability.
5. Suitability of recommended support.
6. Decision to proceed and actual receipt.
7. Engagement and continued use.
8. Functional effectiveness and individual benefit.
9. Satisfaction.
10. Longer-term health and wellbeing outcomes.

These dimensions should initially be reported separately.

Do not create a single overall health or wellbeing success score until its construction, assumptions, weighting and validation have been explicitly justified.

Outcomes should be connected to individual goals and relevant evidence. Missing information must not be interpreted as a negative outcome.

## 7. Research evidence classification

All model inputs, relationships and outcome measures must be identified according to their evidence status:

- **Evidence-supported:** grounded in relevant research, validated measures or authoritative policy documentation.
- **Simulation assumption:** an explicitly defined provisional parameter used for experimentation.
- **Not yet established:** a relationship for which adequate evidence, measurement or calibration is unavailable.

The simulator must not present illustrative costs, behavioural probabilities, service-use rates or effectiveness parameters as measured population estimates.

Evidence must be relevant to the population, setting, intervention and outcome being modelled. Where evidence is limited or indirect, that limitation must be recorded.

## 8. Implementation status and development

This document describes the intended modelling framework. It does not imply that every health and wellbeing domain, service pathway, funding arrangement or outcome measure is currently implemented.

The existing implementation should be extended incrementally. New domains should retain the distinctions and evidence principles described here without assuming that one domain's variables or relationships apply universally.
