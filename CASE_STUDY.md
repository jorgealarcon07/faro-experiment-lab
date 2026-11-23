# Case study · Testing an extra payment reminder

[Español](CASO_DE_ESTUDIO.md) · [Run the synthetic demo](README.md#run-the-synthetic-demo)

## The decision

Operations wants to know whether an extra reminder brings forward enough payments to justify its cost and any increase in complaints. The data team needs a design that can distinguish the effect of assigning a reminder from the fact that some accounts are easier to reach.

## What I built

I fixed the protocol, random seeds and thresholds before generating results. The simulator assigns eligible accounts independently with a 50% chance of treatment and measures full payment at 14 days. It allows two additional days for events to arrive. The decision requires the lower 95% confidence bound for the payment difference to exceed one percentage point, the lower bound on incremental cash to be positive and the upper bound on extra complaints to stay below half a percentage point. The analysis keeps every account in its assigned group. [Protocol](experiment_protocols/v1.json) · [Pre-experiment power calculation](experiment_protocols/power_before_run.json)

## What the test showed

- In the favorable scenario with **20,000 simulated accounts**, 2,315 of 9,958 treatment accounts paid in full, compared with 2,003 of 10,042 controls. The estimated difference by assignment was **+3.30 percentage points**, with a 95% confidence interval of **+2.16 to +4.44**. The payment, complaint and cash rules produced `ship` in that scenario. The scenario with more complaints produced `hold`. [Scenario results and assumptions](reports/release/cases.json)
- Comparing only the accounts that received the message would have yielded **+5.93 percentage points** in the favorable scenario. Restricting the comparison by successful delivery favors people who were easier to reach and already more likely to pay in the simulator. [Open interactive report](https://jorgealarcon07.github.io/jorgealarcon07/experimento-de-recordatorios/index.en.html)
- I removed **3,250 treatment outcomes** from a copy. The allocation registry still looked balanced, while the analyzed records showed a large imbalance. The pipeline returned `invalid` and withheld estimates. Restoring the outcomes produced a new reviewed run and preserved the rejected version. [Run manifests](reports/release/manifests.json) · [Verification](reports/release/verification.json)

## What I learned

The allocation can pass a balance check while the analyzed records fail it. I tested the decision procedure over 5,000 simulated replications across five scenarios. In the A/A scenario it rejected zero in 46 out of 1,000 replications. A real rollout would still need a pilot with measured costs, complaints and payment behavior after day 14. [Monte Carlo results](reports/release/monte_carlo.json) · [English walkthrough transcript](assets/web/walkthrough.en.txt)
