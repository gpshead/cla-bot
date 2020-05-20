import { EdgeDBRepository } from "./base";
import { injectable } from "inversify";
import {
  AgreementsRepository,
  AgreementListItem,
  AgreementText,
  RepositoryAgreementInfo,
  Agreement,
  AgreementVersion,
  getDefaultVersionNumber
} from "../../domain/agreements";


interface IVersion {
  id: string
  number: string
  current: boolean
  creation_time: string
}


@injectable()
export class EdgeDBAgreementsRepository
  extends EdgeDBRepository implements AgreementsRepository {

  async getAgreement(agreementId: string): Promise<Agreement | null> {
    const items = await this.run(async (connection) => {
      return await connection.fetchAll(
        `SELECT Agreement {
          name,
          description,
          creation_time,
          versions: {
            number,
            current,
            creation_time
          }
        }  FILTER .id = <uuid>$id;`,
        {
          id: agreementId
        }
      )
    })

    if (!items.length)
      // agreement not found
      return null;

    const agreement = items[0];
    const versions = agreement.versions as IVersion[];

    return new Agreement(
      agreement.id,
      agreement.name,
      agreement.description,
      agreement.creation_time,
      versions.map(entity => new AgreementVersion(
        entity.id,
        entity.number,
        entity.current,
        new Date(entity.creation_time),
        []
      ))
    )
  }

  async updateAgreement(
    id: string,
    name: string,
    description: string
  ): Promise<void> {
    await this.run(async (connection) => {
      await connection.fetchOne(
        `
        UPDATE Agreement
        FILTER .id = <uuid>$id
        SET {
          name := <str>$name,
          description := <str>$description,
          update_time := <datetime>$update_time,
        }
        `,
        {
          id,
          name,
          description,
          update_time: new Date()
        }
      )
    })
  }

  async getCurrentAgreementVersionForRepository(
    repositoryFullName: string
  ): Promise<RepositoryAgreementInfo | null> {
    const items = await this.run(async (connection) => {
      return await connection.fetchAll(
        `SELECT Repository {
          agreement: {
            versions: {
              number
            } FILTER .current = True and .texts.culture = <str>$culture LIMIT 1
          }
        } FILTER .full_name = <str>$full_name;`,
        {
          culture: "en",
          full_name: repositoryFullName
        }
      )
    })

    if (!items.length)
      return null;

    const currentVersion = items[0].license?.versions[0];
    return new RepositoryAgreementInfo(
      currentVersion.id,
      currentVersion.number.toString()
    )
  }

  async getAgreementTextForRepository(
    repositoryFullName: string,
    cultureCode: string
  ): Promise<AgreementText | null> {
    const items = await this.run(async (connection) => {
      return await connection.fetchAll(
        `SELECT Repository {
          agreement: {
            versions: {
              number,
              texts: {
                text,
                title,
                culture
              } FILTER .culture = <str>$culture LIMIT 1
            } FILTER .current = True LIMIT 1
          }
        } FILTER .full_name = <str>$full_name;`,
        {
          culture: "en",
          full_name: repositoryFullName
        }
      )
    })

    if (!items.length)
      return null;

    const currentVersion = items[0].license?.versions[0];
    const versionText = currentVersion.texts[0];
    return new AgreementText(
      versionText.title,
      versionText.text,
      cultureCode,
      currentVersion.id
    )
  }

  async getAgreementText(
    versionId: string,
    cultureCode: string
  ): Promise<AgreementText | null> {
    const items = await this.run(async (connection) => {
      return await connection.fetchAll(
        `SELECT AgreementVersion {
          texts: {
            text,
            title,
            culture
          } FILTER .culture = <str>$culture LIMIT 1
        } FILTER .id = <uuid>$version_id;`,
        {
          culture: cultureCode,
          version_id: versionId
        }
      )
    })

    if (!items.length)
      return null;

    const version = items[0];
    const text = version.texts[0];
    return new AgreementText(
      text.title,
      text.text,
      text.culture,
      version.id
    )
  }

  async getLicenseForRepository(
    fullRepositoryName: string,
    cultureCode: string
  ): Promise<string | null> {
    const items = await this.run(async (connection) => {
      return await connection.fetchAll(
        `SELECT Repository {
          agreement: {
            versions: {
              texts: {
                text
              } FILTER .culture = <str>$culture
            } FILTER .current = True
          }
        } FILTER .full_name = <str>$full_name;`,
        {
          culture: cultureCode,
          full_name: fullRepositoryName
        }
      )
    })

    if (!items.length)
      return null;

    const item = items[0];
    return item.license?.versions[0]?.texts[0]?.text || null;
  }

  async getAgreements(): Promise<AgreementListItem[]> {
    const items = await this.run(async (connection) => {
      return await connection.fetchAll(
        `SELECT Agreement {
          name,
          description,
          creation_time
        };`
      );
    })

    return items.map(entity => new AgreementListItem(
      entity.id,
      entity.name,
      entity.description,
      entity.creation_time
    ));
  }

  async createAgreement(
    name: string,
    description?: string
  ): Promise<AgreementListItem> {
    // For best UX, a new agreement is created with a starting
    // version and English text

    return await this.run(async connection => {
      const creationTime = new Date();
      const result = await connection.fetchAll(
        `
        INSERT Agreement {
          name := <str>$name,
          description := <str>$description,
          creation_time := <datetime>$creation_time,
          versions := {
              (INSERT AgreementVersion {
                  number := <str>$initial_version_number,
                  current := False,
                  texts := (
                      (INSERT AgreementText {
                          text := <str>$initial_text,
                          culture := <str>$initial_culture,
                          update_time := datetime_current()
                      })
                  )
              })
          }
      };
        `,
        {
          name: name,
          description: description || "",
          creation_time: creationTime,
          initial_text: "Lorem ipsum dolor sit amet",
          initial_culture: "en",
          initial_version_number: getDefaultVersionNumber()
        }
      )
      const item = result[0];
      return new AgreementListItem(
        item.id,
        name,
        description,
        creationTime
      );
    });
  }
}
