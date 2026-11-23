'use strict';

const DAY_MS = 86_400_000;
const IST_MS = 19_800_000;
const MONTH_DAY_LCM = 377580n;
const FRACTION_DENOMINATOR = 50n * MONTH_DAY_LCM;

function istDate(time) {
  return new Date(time + IST_MS).toISOString().slice(0, 10);
}

function midnight(date) {
  const utc = Date.parse(date + 'T00:00:00Z');
  if (!Number.isFinite(utc) || new Date(utc).toISOString().slice(0, 10) !== date) {
    throw Error('Invalid IST date: ' + date);
  }
  return utc - IST_MS;
}

function wholeCoins(value) {
  if (!Number.isSafeInteger(value) || value < 0) throw Error('Invalid coin value');
  return BigInt(value);
}

function dailyCredit(principal, date, carry) {
  const [year, month] = date.split('-').map(Number);
  const days = BigInt(new Date(Date.UTC(year, month, 0)).getUTCDate());
  const units = wholeCoins(principal) * 3n * (MONTH_DAY_LCM / days) + wholeCoins(carry);
  return {
    amount: Number(units / FRACTION_DENOMINATOR),
    carry: Number(units % FRACTION_DENOMINATOR)
  };
}

async function settleWallet(db, walletRef, startDate, today, serverTimestamp) {
  const stateRef = walletRef.collection('commissionState').doc('daily');

  for (;;) {
    const advanced = await db.runTransaction(async tx => {
      const wallet = await tx.get(walletRef);
      if (!wallet.exists) return false;

      const state = (await tx.get(stateRef)).data();
      if (state && state.startDate !== startDate) {
        throw Error('Commission start date differs from stored state');
      }

      const date = state?.nextDate ?? startDate;
      if (date >= today) return false;

      const cutoff = midnight(date) + DAY_MS;
      const history = walletRef.collection('transactions');
      const creditRef = history.doc('daily_commission_' + date);

      if ((await tx.get(creditRef)).exists) {
        throw Error('Commission transaction exists without matching cursor: ' + date);
      }

      // Reverse principal changes made after this IST day ended.
      const changes = await tx.get(history
        .where('createdAt', '>=', new Date(cutoff))
        .select('type', 'amount'));
      let principal = wholeCoins(wallet.get('principalCoins'));

      for (const entry of changes.docs) {
        const type = entry.get('type');
        if (type === 'principal_add') principal -= wholeCoins(entry.get('amount'));
        if (type === 'principal_deduct') principal += wholeCoins(entry.get('amount'));
      }

      const {amount, carry} = dailyCredit(Number(principal), date, state?.carry ?? 0);

      if (amount > 0) {
        const balance = wholeCoins(wallet.get('commissionCoins')) + BigInt(amount);
        wholeCoins(Number(balance));
        tx.update(walletRef, {
          commissionCoins: Number(balance),
          lastTransactionId: creditRef.id
        });
        tx.create(creditRef, {
          type: 'daily_commission',
          amount,
          createdAt: serverTimestamp()
        });
      }

      tx.set(stateRef, {startDate, nextDate: istDate(cutoff), carry});
      return true;
    });

    if (!advanced) return;
  }
}

async function main() {
  const startDate = process.env.COMMISSION_START_IST;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(startDate ?? '')) {
    throw Error('Set COMMISSION_START_IST before running.');
  }
  midnight(startDate);

  const {Firestore, FieldPath, FieldValue} = require('@google-cloud/firestore');
  const db = new Firestore({projectId: 'lucky-lottery-1d174'});
  const today = istDate(Date.now());
  const wallets = db.collection('walletClients')
    .orderBy(FieldPath.documentId()).select().limit(100);
  let page = await wallets.get();
  let failed = 0;

  while (!page.empty) {
    for (const wallet of page.docs) {
      try {
        await settleWallet(db, wallet.ref, startDate, today, FieldValue.serverTimestamp);
      } catch (error) {
        failed++;
        console.error('Wallet settlement failed for %s: %s', wallet.id, error.message);
      }
    }
    page = await wallets.startAfter(page.docs.at(-1)).get();
  }

  if (failed) throw Error(failed + ' wallet(s) failed settlement.');
}

module.exports = {dailyCredit, istDate, midnight, settleWallet};

if (require.main === module) {
  main().catch(error => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
