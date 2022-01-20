import e from "../../../dbschema/edgeql";

import {ContributorLicenseAgreement, ClaRepository} from "../../domain/cla";
import {EdgeDBRepository} from "./base";
import {injectable} from "inversify";

@injectable()
export class EdgeDBClaRepository
  extends EdgeDBRepository
  implements ClaRepository
{
  async getClaByEmailAddress(
    email: string
  ): Promise<ContributorLicenseAgreement | null> {
    return await this.run(async (connection) =>
      e
        .select(e.ContributorLicenseAgreement, (cla) => ({
          id: true,
          email: true,
          username: true,
          versionId: cla.agreement_version.id,
          signedAt: cla.creation_time,

          filter: e.op(cla.email, "=", email),
        }))
        .run(connection)
    );
  }

  async saveCla(data: ContributorLicenseAgreement): Promise<void> {
    await this.run(async (connection) =>
      e
        .insert(e.ContributorLicenseAgreement, {
          email: data.email,
          username: data.username,
          agreement_version: e.assert_exists(
            e.select(e.AgreementVersion, (a) => ({
              filter: e.op(a.id, "=", e.uuid(data.versionId)),
            }))
          ),
          creation_time: data.signedAt,
        })
        .run(connection)
    );
  }
}
